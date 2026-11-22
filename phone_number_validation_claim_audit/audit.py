"""Offline, syntax-only documentation and source inspection."""
import ast
import os
import re
from pathlib import Path
from .phrases import PHONEVALIDATION, NOPHONEVALIDATION, GENERIC

VALIDATORS = frozenset(('is_valid_number', 'is_possible_number', 'is_valid_number_for_region', 'is_possible_number_with_reason', 'is_possible_number_string', 'is_possible_number_for_type', 'is_possible_number_for_type_with_reason', 'is_valid_short_number', 'is_possible_short_number'))

def _pattern(phrases):
    return re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(p) for p in sorted(phrases, key=lambda p: (-len(p), p))) + r')(?!\w)')
YES = _pattern(PHONEVALIDATION)
NO = _pattern(NOPHONEVALIDATION)

def doc_claims(text):
    lines = []
    fence = None
    for line in text.splitlines():
        m = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = None
            continue
        if m:
            fence = m.group(1)
            lines.append('')
        else:
            lines.append(line)
    found_yes, found_no = [], []
    for para in re.split(r'\n\s*\n', '\n'.join(lines)):
        para = re.sub(r'\s+', ' ', para.lower().replace("n't", ' not').replace('-', ' '))
        found_no.extend(m.group() for m in NO.finditer(para))
        para = NO.sub(' ', para)
        found_yes.extend(m.group() for m in YES.finditer(para))
    return found_yes, found_no

def _root(node):
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else None

def _chain(node):
    result = []
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        if isinstance(node, ast.Attribute):
            result.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            node = node.value
    return result

def _targets(node):
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        return set().union(*(_targets(x) for x in node.elts)) if node.elts else set()
    return set()

def source_evidence(text):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return False
    imports, bound, defined = {}, set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                imports[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            for a in n.names:
                if a.name != '*':
                    imports[a.asname or a.name] = n.module + '.' + a.name
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(n.name)
        elif isinstance(n, ast.Assign):
            for target in n.targets:
                bound.update(_targets(target))
        elif isinstance(n, ast.AnnAssign):
            bound.update(_targets(n.target))
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            for item in n.items:
                if item.optional_vars:
                    bound.update(_targets(item.optional_vars))
    shadow = defined | bound
    parse_leg = method_leg = False
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name):
            if f.id in shadow or f.id not in imports:
                continue
            resolved = imports[f.id]
            last = resolved.rsplit('.', 1)[-1]
            if last in GENERIC and last not in defined:
                return True
            if resolved.startswith('phonenumbers.') and last not in defined:
                if last in VALIDATORS:
                    return True
                if last == 'parse':
                    parse_leg = True
        elif isinstance(f, ast.Attribute):
            name = f.attr
            base = _root(f.value)
            if name in defined or (base in imports and base in shadow):
                continue
            if name in GENERIC:
                return True
            library = base in imports and (imports[base] == 'phonenumbers' or imports[base].startswith('phonenumbers.'))
            if name in VALIDATORS:
                method_leg = True
                if library:
                    return True
            if name == 'parse' and library:
                parse_leg = True
            if name == 'fetch':
                chain = _chain(f.value)
                if 'phone_numbers' in chain and 'lookups' in chain[chain.index('phone_numbers') + 1:]:
                    return True
    return parse_leg and method_leg

def audit(root, ignore=()):
    root = Path(root)
    if not root.is_dir() or not os.access(root, os.R_OK | os.X_OK):
        raise OSError('not a readable directory: ' + str(root))
    ignores = [p.replace('\\', '/').strip('/') for p in ignore]
    def ignored(path):
        s = path.as_posix()
        return any(s == p or s.startswith(p + '/') for p in ignores if p)
    docs, production, tests = [], [], []
    def onerror(error):
        raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        base = Path(directory)
        dirs[:] = sorted(d for d in dirs if not (base / d).is_symlink() and not ignored((base / d).relative_to(root)))
        for filename in sorted(files):
            path = base / filename
            rel = path.relative_to(root)
            if path.is_symlink() or ignored(rel):
                continue
            parts = rel.parts
            if (rel.as_posix() == 'README.md' or ('docs' in parts and path.suffix == '.md')):
                docs.append((rel.as_posix(), path.read_text(encoding='utf-8')))
            if path.suffix == '.py' and not any(x in parts for x in ('fixtures', 'docs', 'examples')):
                is_test = 'tests' in parts or filename.startswith('test_') or filename.endswith('_test.py')
                (tests if is_test else production).append((rel.as_posix(), path.read_text(encoding='utf-8')))
    claims, denials = [], []
    for path, content in docs:
        y, n = doc_claims(content)
        claims.extend({'path': path, 'phrase': phrase} for phrase in y)
        denials.extend({'path': path, 'phrase': phrase} for phrase in n)
    prod = [path for path, content in production if source_evidence(content)]
    test = [path for path, content in tests if source_evidence(content)]
    findings = []
    if claims and not prod:
        findings.append({'id': 'documented-phone-validation-claim-false', 'severity': 'MEDIUM' if test else 'HIGH', 'claims': claims, 'evidence': test})
    if denials and prod:
        findings.append({'id': 'documented-no-phone-validation-claim-false', 'severity': 'HIGH', 'claims': denials, 'evidence': prod})
    return {'findings': findings, 'production_evidence': prod, 'test_evidence': test}
