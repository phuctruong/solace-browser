# TASK-002 Frontend State Machines

## Page Flow

```mermaid
stateDiagram-v2
    [*] --> HomeLoading
    HomeLoading --> HomeLoaded: apps + credits + runs fetched
    HomeLoading --> HomeError: any fetch fails

    HomeLoaded --> ApprovalPreview: run now
    ApprovalPreview --> ApprovalSubmitting: approve / abort / modify
    ApprovalSubmitting --> HomeLoaded: success
    ApprovalSubmitting --> ApprovalError: request fails
    ApprovalError --> ApprovalPreview: retry
    ApprovalPreview --> HomeLoaded: close

    [*] --> LoginIdle
    LoginIdle --> LoginSubmitting: google popup / email form
    LoginSubmitting --> LoginSuccess: auth + browser register succeed
    LoginSubmitting --> LoginError: validation / auth failure
    LoginError --> LoginSubmitting: retry
    LoginSuccess --> [*]

    [*] --> AppDetailLoading
    AppDetailLoading --> AppDetailLoaded: manifest fetched
    AppDetailLoading --> AppDetailError: fetch fails
    AppDetailLoaded --> ApprovalPreview: run now
    AppDetailLoaded --> AppDetailLoaded: uninstall cancelled
    AppDetailLoaded --> HomeLoaded: uninstall confirmed

    [*] --> RunLoading
    RunLoading --> RunLoaded: run fetched
    RunLoading --> RunError: fetch fails
    RunLoaded --> RunLoading: rerun

    [*] --> LLMIdle
    LLMIdle --> LLMValidating: validate key
    LLMValidating --> LLMReady: key valid / managed selected
    LLMValidating --> LLMError: invalid key / request fails
    LLMReady --> [*]

    [*] --> MembershipLoading
    MembershipLoading --> MembershipLoaded: plans fetched
    MembershipLoading --> MembershipError: fetch fails
    MembershipLoaded --> CheckoutSubmitting: upgrade
    CheckoutSubmitting --> MembershipRedirect: checkout url returned
    CheckoutSubmitting --> MembershipError: request fails
```

## Notes

- Every page has exactly `loading`, `loaded`, and `error` states.
- Approval uses a nested FSM because both Home and App Detail can open it.
- Login has both popup auth and email/password auth, but they share one submit/error path.
- `RunDetailPage` re-run returns to `RunLoading` so the UI can refresh from the same endpoint.
