# Documentation claim auditor

This offline static auditor compares documented claims about judging whether a number is well-formed, possible, or valid for a region with Python source evidence. It never executes inspected code.

## Usage

```sh
PIP_NO_CACHE_DIR=1 python3 -m pip install .
phone-number-validation-claim-audit audit . --json
python3 -m phone_number_validation_claim_audit audit . --verbose
```

The path defaults to the current directory. Repeat `--ignore PREFIX` to exclude paths. Use `--fail-on medium` to include test-only findings. Exit status is 0 for PASS, 2 for findings at the chosen threshold, and 1 for usage or I/O errors. Use `--version` to show the version.

Finding identifiers:

```text
documented-phone-validation-claim-false
documented-no-phone-validation-claim-false
```

## Differentiation

Other families cover SMS sending, email sending and email validation, authentication with a one-time code, extraction of a number from a document, and barcode and QR decoding from an image. This audit also excludes formatting for display, carrier, place name or timezone lookup, and finding numbers in running text.

Other families cover spreadsheet reading and generation, word-document reading and generation, presentation reading and generation, PDF extraction, generation, merging, splitting, encryption, rotation, form-filling, watermarking, redaction, compression and annotation, table extraction, OCR, document extraction, e-signature, payment processing, screen recording, video editing and generation, QR code generation, barcode generation and scanning, audio mixing, audio generation, audio editing, source separation, speech recognition, text-to-speech, noise suppression, music generation and music transcription.

## Limitations

- This phrase may describe browser-side form checks:

  ```text
  validate phone number
  ```

- This phrase may mean checking only for presence:

  ```text
  check phone number
  ```

- This phrase may describe a roadmap item:

  ```text
  phone number validation
  ```

- This phrase may name a person or a hosted page:

  ```text
  phone number validator
  ```

- This phrase may describe correct human entry without a check:

  ```text
  valid phone number
  ```

- This phrase may omit the region needed to judge dialling:

  ```text
  phone number is valid
  ```

- This phrase may describe rejecting a duplicate or blocked prefix:

  ```text
  reject invalid phone number
  ```

- This phrase may describe a manual runbook step:

  ```text
  check if phone number is valid
  ```

- This phrase may mean checking only for presence:

  ```text
  validate mobile number
  ```

- A parse and a qualifying method call on an unrelated object count together.
- The pair does not trace data flow from the parsed object.
- A library check counts regardless of where its argument originated.
- A lookup call counts even in code that never runs.
- Both v1 and v2 lookup chains count.
- A lookup chain hidden behind a variable can be missed.
- An import alone is not evidence.
- Roadmap, changelog and TODO prose still counts.
- Denials outside the list are not recognised.
- Documents outside the root README and docs directories are ignored.
- Evidence split across modules is missed.
- Local definitions shadow route names, including wrappers.
- Dead code counts.
- Subprocess calls invoking external tools are not evidence.
- SMS sending alone is not evidence.
- Email validation alone is not evidence.
- Authentication alone is not evidence.
- Extraction alone is not evidence.
- A locally defined generic name is shadowed.
- Successive alias chains can be missed.
- Only exact phrases are matched; meaning is not inferred.
- Implementations in other languages are invisible.
- Runtime-only routes are invisible.
- The parse and method calls must occur in one module.
- Parsing alone is not evidence.
- Formatting alone is not evidence.
- Constructing a number object alone is not evidence.
- Finding numbers in text alone is not evidence.
- Formatting keystrokes alone is not evidence.
- A geocoder, carrier or timezone lookup alone is not evidence.
- A bare fetch call is not evidence.
- A verification check alone is not evidence.
- Static matching does not establish correctness.
