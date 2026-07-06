"""Execution Engine — observable, replayable, auditable, cancellable, resumable execution of approved Recovery Plans.

Extension points for future actions (no redesign required):
- Register new actions via ActionRegistry.register(action_type, ActionClass)
- Add rollback steps by setting rollback_available=True and implementing RollbackAction
- Add automatic approval by introducing mode="assisted" or mode="automatic"
- Add notifications by implementing NotifyUserAction and appending to execution plans
- Add import verification by implementing ImportVerificationAction
- Add alternative grabbing by implementing GrabAlternativeAction
"""
