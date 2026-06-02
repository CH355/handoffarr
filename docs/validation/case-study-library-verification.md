# Case Study — Library Verification Blocked by Container Path Authority

## Symptoms

- `/api/imports` reported `Import Success` for the affected items.
- `/api/debug/correlation` confirmed path mapping was producing the expected
  destination path strings.
- The library files were verifiable on the host filesystem.
- `/api/library` consistently reported `Library Present = 0` and classified
  every item as `Library Unknown` or `Library Missing`.

## Evidence

- `/api/debug/library` showed the library collector probing the mapped path
  and receiving `file_exists = False` for every artefact.
- The host running Handoffarr could `ls` the files at the same path that the
  collector was probing.
- The collector reported a successful path translation, so the mismatch was
  not a path-mapping bug.
- Comparing the container's view of the volume against the host showed the
  Handoffarr container did not have the library volume mounted with the same
  authority — the bind mount existed but the directory inside the container
  was empty.

## Root cause

Handoffarr's filesystem collector trusts that paths derived from path
mapping are reachable inside its own process. They are not, unless the
library volume is mounted into the Handoffarr container with read access at
the *same* path the *arr application uses. In the failing deployment, the
path translation produced `/library/...` paths but the container only had
`/data/...` mounted. The translation was correct for the *arr container,
not for Handoffarr.

This means library verification depended on a deployment invariant
(matching mounts) that nothing was enforcing or surfacing.

## Corrective action

1. Library collector now records `path_verified` evidence on every probe so
   downstream interpreters can distinguish "we checked and the file isn't
   there" from "we never had visibility on this path".
2. Library interpreter (`app/library.py`) only emits `Library Missing` when
   `path_verified` is explicitly `False`; otherwise the artefact stays
   `Library Unknown`. This prevents the dashboard from claiming a library
   regression that is really a container visibility gap.
3. `/api/validation` now includes a Library check that fails loudly when
   import successes exist but no library artefacts verify, so the
   visibility gap shows up as a validation failure instead of silent zeroes.
4. README and `docs/architecture/storage-model.md` should call out that the
   library volume must be mounted into Handoffarr at the same path the
   *arr container uses; until then the case study stands as the canonical
   reference.

## Lessons learned

- Path authority is a deployment fact, not a code fact. Handoffarr's
  collectors must report on whether they had authority, not just on what
  they found.
- "Zero" is dangerous when it can mean either "nothing exists" or
  "I cannot see it". Interpreters should refuse to classify until the
  authority question is answered.
- Validation that compares an interpreter's view against the host filesystem
  catches this class of bug; the automated checks in `app/validation.py`
  exist specifically to surface it next time.
