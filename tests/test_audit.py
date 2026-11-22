import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from phone_number_validation_claim_audit.audit import audit, doc_claims, source_evidence, VALIDATORS
from phone_number_validation_claim_audit.phrases import PHONEVALIDATION, NOPHONEVALIDATION, GENERIC

class AuditTests(unittest.TestCase):
    def test_phrases(self):
        self.assertEqual((len(set(PHONEVALIDATION)), len(set(NOPHONEVALIDATION)), len(set(GENERIC))), (50, 24, 24))
        for phrase in PHONEVALIDATION:
            with self.subTest(phrase=phrase): self.assertTrue(doc_claims(phrase)[0])
        for phrase in NOPHONEVALIDATION:
            with self.subTest(phrase=phrase): self.assertEqual(doc_claims(phrase), ([], [phrase]))
        self.assertEqual(doc_claims('```\nvalidate phone number\n```\n\n`validate-phone-number`')[0], ['validate phone number'])
        self.assertEqual(doc_claims("doesn't validate phone number"), ([], ['does not validate phone number']))

    def test_routes(self):
        for name in VALIDATORS:
            for source in ('import phonenumbers as p\np.'+name+'()', 'from phonenumbers import '+name+' as f\nf()', 'import phonenumbers as p\np.parse()\nobj.'+name+'()'):
                with self.subTest(source=source): self.assertTrue(source_evidence(source))
        for name in GENERIC:
            for source in ('obj.'+name+'()', 'from lib import '+name+' as f\nf()'):
                with self.subTest(source=source): self.assertTrue(source_evidence(source))
        for version in ('v1', 'v2'):
            self.assertTrue(source_evidence('client.lookups.'+version+'.phone_numbers("x").fetch()'))
        self.assertTrue(source_evidence('from phonenumbers import parse as p\np()\nx.is_valid_number()'))
        self.assertTrue(source_evidence('import phonenumbers\nn = phonenumbers.parse()\nn.is_valid_number()'))

    def test_non_evidence(self):
        cases = ['import phonenumbers', 'import phonenumbers\nphonenumbers.parse()', 'parse()', 'x.is_valid_number()', 'phonenumbers.format_number()', 'phonenumbers.PhoneNumber()', 'phonenumbers.PhoneNumberMatcher()', 'phonenumbers.AsYouTypeFormatter()', 'geocoder.description_for_number()', 'carrier.name_for_number()', 'timezone.time_zones_for_number()', 'client.messages.create()', 'client.verify.services().verifications.create()', 'client.verify.services().verification_checks.create()', 'client.lookups', 'client.lookups.v2.phone_numbers()', 'x.fetch()', 'client.phone_numbers().fetch()', 'client.lookups.fetch()', 'subprocess.run("validate phone number")', 'email.validate()', 'sms.send()', 'auth.login()', 'extract.phone()', 'cv2.QRCodeDetector().detectAndDecode()', '"validate phone number"', 'validate_phone_number', 'def broken(:']
        cases += [name+'()' for name in VALIDATORS]
        cases += ['def '+name+'(): pass\nx.'+name+'()' for name in GENERIC]
        cases += ['import phonenumbers as p\np = object()\np.is_valid_number()', 'import phonenumbers as p\nwith thing() as p: pass\np.is_valid_number()', 'from phonenumbers import is_valid_number as f\nf = 1\nf()']
        for source in cases:
            with self.subTest(source=source): self.assertFalse(source_evidence(source))

    def test_findings_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'README.md').write_text('validate phone number')
            self.assertEqual(audit(root)['findings'][0]['severity'], 'HIGH')
            (root/'tests').mkdir(); (root/'tests/test_x.py').write_text('x.validate_phone_number()')
            self.assertEqual(audit(root)['findings'][0]['severity'], 'MEDIUM')
            (root/'app.py').write_text('x.validate_phone_number()')
            self.assertFalse(audit(root)['findings'])
            (root/'README.md').write_text('does not validate phone number')
            self.assertEqual(audit(root)['findings'][0]['severity'], 'HIGH')
            self.assertFalse(audit(root, ['app.py'])['findings'])
            (root/'app.py').write_text('import phonenumbers\nphonenumbers.parse()')
            (root/'other.py').write_text('x.is_valid_number()')
            (root/'README.md').write_text('validate phone number')
            self.assertEqual(audit(root)['findings'][0]['severity'], 'MEDIUM')
            (root/'tests/test_x.py').unlink()
            self.assertEqual(audit(root)['findings'][0]['severity'], 'HIGH')
            (root/'README.md').write_text('does not validate phone number')
            self.assertFalse(audit(root)['findings'])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'README.md').write_text('validate phone number')
            cmd = [sys.executable, '-m', 'phone_number_validation_claim_audit']
            p = subprocess.run(cmd + ['audit', tmp, '--json'], capture_output=True, text=True)
            self.assertEqual(p.returncode, 2); self.assertEqual(json.loads(p.stdout)['findings'][0]['severity'], 'HIGH')
            self.assertEqual(subprocess.run(cmd + ['audit', '/missing-r251'], capture_output=True).returncode, 1)
            self.assertEqual(subprocess.run(cmd + ['audit', '--fail-on', 'bad'], capture_output=True).returncode, 1)
            self.assertEqual(subprocess.run(cmd + ['--version'], capture_output=True, text=True).stdout.strip(), '0.1.0')

    def test_self_audit(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(doc_claims((root/'README.md').read_text()), ([], []))
        self.assertFalse(audit(root)['findings'])
