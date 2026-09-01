# UTRANS Change Review

This context covers the review of changes detected between county road data and UTRANS roads. It distinguishes the detected change from the optional UTRANS road it may reference.

## Language

**DFC result**:
A detected feature-change record that a reviewer assesses against county road data and, when present, a linked UTRANS road.
_Avoid_: DFC record, detected change

**Change status**:
The review outcome stored on a DFC result: `COMPLETED`, `IGNORE`, or `REVISIT`.
_Avoid_: DFC disposition

**Linked UTRANS road**:
The UTRANS road referenced by a DFC result as its target road. A DFC result may have no linked UTRANS road.
_Avoid_: target road segment

**Unlinked new record**:
A DFC result with change type `N` and no target UTRANS road. It can be added as a new UTRANS road or assigned a non-completed change status.
_Avoid_: driveway candidate
