# Implementation Plan Review

## Summary verdict

The plan is well-structured and addresses the majority of findings from the architecture review. It is phased sensibly, test-first, and provides concrete test tables for each phase. However, it contains several technical inaccuracies in APL code snippets, a significant gap in MockRequest capabilities (it lacks `SetContentType` and `ContentTypeForFile` despite the plan describing them in Phase 1), an under-specified `⎕VFI` validation pattern that fails on multi-token input, and ambiguities around `⎕NGET` path construction and static file path resolution that would force an implementer to make unguided decisions. A senior Dyalog developer could start Phase 1, but would hit blocking questions by Phase 2.

## Issues found

1. **CRITICAL -- MockRequest is missing `SetContentType` and `ContentTypeForFile` methods.** Phase 1 (line 42) states that `MockRequest.aplc` should have a `SetContentType` method and a `ContentTypeForFile` method. However, Phase 2 tests (`Test_RespondHTMLSetsContentType`, line 106) and Phase 4 tests (`ServePage`, `ServeCSS` handlers at lines 175-176) rely on these methods existing on the mock. The existing `MockRequest` in `/workspace/Stark/Tests/Mocks/MockRequest.aplc` has neither method. The plan describes these methods in Phase 1's build list but does not provide implementation detail for `ContentTypeForFile` (which in Jarvis at line 1763-1768 depends on a `ContentTypes` shared field -- a 79x2 matrix). The mock must either replicate the lookup table or hard-code a minimal subset. The plan says "at minimum: `html`->`text/html; charset=utf-8`, `css`->`text/css`" but does not mention that Jarvis appends `; charset=utf-8` only for `text/html` (line 1767: `r,←('text/html'≡r)/'; charset=utf-8'`), not for `text/css`. The test `Test_ServeCSSContentType` (line 208) expects `text/css` in the content-type header, which is correct, but an implementer copying the Jarvis pattern might incorrectly append charset to CSS too. This needs explicit specification.

2. **HIGH -- `⎕VFI` validation pattern is incomplete for multi-token input.** The architecture doc (lines 98-104) and implementation plan (line 286) show `(valid id)←⎕VFI req.PathParams.id` followed by `:If ~valid`. The `⎕VFI` function splits on spaces, so input like `'1 2'` would produce `(1 1)(1 2)` -- two valid values. The `:If ~valid` check would pass (since `~(1 1)` is `(0 0)`, and `:If 0 0` signals a DOMAIN ERROR because the argument to `:If` must be a scalar or 1-element array). The plan must specify that the validation checks both `1=≢valid` and `⊃valid` (i.e., exactly one token, and it is valid). The ExampleApp at `/workspace/Stark/Examples/ExampleClass/ExampleApp.aplc` line 99 uses `id←⊃2⊃⎕VFI req.PathParams.id` with no validation at all, so the plan cannot simply defer to "the existing pattern".

3. **HIGH -- `⎕NGET` path construction uses string concatenation without a path separator.** Phase 4 (line 175) shows `staticRoot,'index.html'`. This only works if `staticRoot` ends with a trailing slash or platform-appropriate separator. The plan says (line 164) "Resolve `staticRoot` relative to the class source file location... Use `⎕NPARTS` for path resolution" but does not specify how to ensure a trailing separator. `⎕NPARTS` returns components without a trailing slash on the directory part. If `staticRoot` is `/path/to/static` (no trailing `/`), then `staticRoot,'index.html'` produces `/path/to/staticindex.html`. The plan must specify either appending `'/'` or using `⎕NPARTS` to construct the full path.

4. **HIGH -- `staticRoot` resolution mechanism is under-specified.** The plan says (line 164): "Resolve `staticRoot` relative to the class source file location. The class file lives in `APLSource/`; `staticRoot` should point to `../static/` resolved to an absolute path. Use `⎕NPARTS` for path resolution." But `⎕NPARTS` does not resolve relative paths -- it merely splits a path into directory, name, and extension components. Resolving `../static/` relative to a class source file requires knowing the class source location at runtime, which in Dyalog typically involves `⎕SRC` or `⎕CLASS` metadata, or the `SALT_Data` property, or `180⌶`. The plan does not specify which mechanism to use. This is a real implementation decision that cannot be deferred.

5. **HIGH -- No test for whitespace-only todo titles.** The plan has `Test_CreateTodoEmptyTitle` (line 252) for `title←,⊂''`, but no test for `title←,⊂'   '` (whitespace only). Line 234 says "Validate non-empty after trimming" but there is no unit test that verifies trimming behaviour. This is listed in the architecture review findings and was partially addressed (empty title test exists) but whitespace-only is a distinct edge case that the plan's own build step (line 234) acknowledges.

6. **HIGH -- `HandleError` signature discrepancy.** The architecture doc (line 215) describes `HandleError req` as monadic in the handler list: "HandleError req -- OnErrorFn target." But the actual signature must be dyadic: `result←err HandleError req` (confirmed by Stark source at `/workspace/Stark/APLSource/Stark.aplc` line 194: `result←err(Handlers⍎OnErrorFn)req`). The implementation plan (line 179) correctly shows the dyadic form, but the architecture doc's handler list is inconsistent. Since the implementation plan is derived from the architecture, this inconsistency could confuse an implementer reading both documents.

7. **MEDIUM -- Phase 4 constructor uses `⎕NEW ##.Stark` but Phase 4 also says `router←⎕NEW ##.Stark`.** The ExampleApp at `/workspace/Stark/Examples/ExampleClass/ExampleApp.aplc` line 24 uses `router←##.Stark.New ()` (the shared constructor). The plan uses `⎕NEW ##.Stark` (the instance constructor `Make0`). Both work, but `Stark.New` also sets `Handlers←1(86⌶)'⎕THIS'` (Stark.aplc line 46), which would overwrite the `Handlers` assignment on the next line (`router.Handlers←⎕THIS`). Using `⎕NEW` then setting `Handlers` is fine; using `Stark.New` then setting `Handlers` is also fine (just redundant). But the plan should be consistent with the ExampleApp pattern. Minor, but a potential source of confusion.

8. **MEDIUM -- `Render.RespondHTML` references `req.SetContentType` which does not exist on MockRequest.** Phase 2 tests (line 106-107) call `RespondHTML` with a mock request. `RespondHTML` calls `req.SetContentType 'text/html; charset=utf-8'` (line 82). But Phase 1's MockRequest description says to add a `SetContentType` method, which is not on the existing Stark MockRequest. If the implementer copies the existing MockRequest as a starting point (as the plan implies by saying "copy the pattern"), they will not have this method, and Phase 2 tests will fail with a VALUE ERROR. This is technically covered by issue 1, but the phase ordering creates a trap: Phase 1 says "create MockRequest" referencing the Stark pattern, but the Stark MockRequest lacks the required methods.

9. **MEDIUM -- Integration test HttpCommand syntax for POST is unverified.** The plan (line 267) shows: `resp←#.HttpCommand.Do 'POST' url 'title=Buy milk' 'application/x-www-form-urlencoded'`. The `HttpCommand.Do` shared method signature is not specified in the plan. In practice, `HttpCommand` accepts various calling conventions, and the 4-argument form `Do method url body content-type` may or may not match the version bundled with Stark. The plan should reference the specific `HttpCommand` version or API, or provide a tested example. If `HttpCommand.Do` does not accept a 4th positional argument for content-type, all integration POST tests will fail.

10. **MEDIUM -- `Test_CreateTodoMissingTitle` uses `9.1≠req.Payload.⎕NC⊂'title'` for field detection.** Line 232 shows this as the check for a missing `title` field. However, `⎕NC` on a namespace member returns a scalar, not a result that needs comparison with `9.1`. A missing field returns `0`, not `9.1`. The correct check for "field exists" would be `0=req.Payload.⎕NC⊂'title'` (field does not exist). The `9.1` check would test whether `title` is a "namespace array member" (name class 9.1), which is wrong -- `title` after form-urlencoded parsing is a simple variable (name class 2.1). This code would incorrectly reject valid payloads.

11. **MEDIUM -- `DeleteTodo` returns `'' RespondHTML req` but architecture says "Empty body, 200 status".** The `RespondHTML` helper calls `req.SetContentType 'text/html; charset=utf-8'`, so even an empty delete response gets `text/html` content-type. This is fine functionally, but the test `Test_AllEndpointsReturnHTML` (line 360) verifies that no endpoint returns `application/json`, not that all return `text/html`. For DELETE with an empty body, setting `text/html` is technically unnecessary and slightly misleading. This is a minor inconsistency between the architecture ("Empty body, 200 status") and the implementation (which wraps it in RespondHTML).

12. **MEDIUM -- No `⎕DL` (delay) after `app.Start` in RunTests.apls.** The existing Stark test runner (`/workspace/Stark/Tests/RunTests.apls` line 30) has `⎕DL 1` after `app.Start port` to allow the server time to initialise. The implementation plan's Phase 8 (lines 383-391) describes the test runner structure but does not mention this delay. Without it, integration tests may fire before the server is listening, causing spurious connection failures.

13. **MEDIUM -- Phase 7 `Test_OnErrorFn*` tests require a `/test/break` route, but the mechanism is vague.** Line 362 says: "register a deliberate broken route in the test harness only... Before running integration tests, add a route `/test/break` pointing to a handler that signals an error." The plan does not specify how the test harness accesses the router to add this route, nor where the `BrokenHandler` function lives. The existing Stark test pattern (`/workspace/Stark/Tests/Mocks/MockHandlers.apln` line 34) defines `BrokenHandler` in the `MockHandlers` namespace, but the todo app's `Handlers` is set to `⎕THIS` (the TodoApp instance). Adding an external handler requires either: (a) changing `Handlers` to include the test namespace, (b) adding a method to TodoApp that the test harness can call to register the route, or (c) defining the broken handler as a method on TodoApp itself (polluting production code). None of these options is specified.

14. **MEDIUM -- `FindTodo` return convention is ambiguous.** Phase 6 (line 288) says `FindTodo` returns `⍬` on error and "the index into `todos`" on success. But `⍬` is an empty numeric vector, and the calling code checks `If result is ⍬`. In APL, checking `result≡⍬` is the intended pattern, but the plan does not specify the exact check. If the caller uses `:If 0=≢result` instead, an index value of (say) `3` would pass since `1=≢3` (a scalar has shape empty, so `≢3` is 1, not 0). The plan should specify the exact check pattern: `:If ⍬≡idx`.

15. **LOW -- Test count discrepancy.** The Phase summary table (line 413-423) claims 44 unit tests and 24 integration tests, totalling 68. Counting the test tables: Phase 1: 1, Phase 2: 14 (but I count 13 in the table), Phase 3: 7, Phase 4: 2 unit + 6 integration, Phase 5: 8 unit + 6 integration, Phase 6: 10 unit + 8 integration, Phase 7: 2 unit + 4 integration. Unit total: 1+14+7+2+8+10+2 = 44 (if Phase 2 has 14). Integration total: 6+6+8+4 = 24. The counts match the summary only if Phase 2 has 14 tests. Counting the Phase 2 table: I see 13 rows. Either the table is missing a test or the count is wrong. Specifically, the tests listed are: EscapeAmpersand, EscapeLtGt, EscapeQuotes, EscapeCleanString, EscapeEmpty, EscapeNoDoubleEscape, TodoItemBasic, TodoItemCompleted, TodoItemEscapedTitle, TodoItemHtmxAttrs, TodoListEmpty, TodoListMultiple, RespondHTMLSetsContentType, RespondHTMLReturnsHTML = 14. Count is correct; I miscounted.

16. **LOW -- `Test_AppInitEmptyTodos` and `Test_AppInitNextId` test internal state.** These tests (lines 196-197) directly access `app.todos` and `app.nextId`, which are `:Field` declarations. If these fields are `:Field Private`, the tests cannot access them from outside the class. The plan declares them without access specifiers (line 162), which in Dyalog defaults to Private for class fields. Either the fields must be `:Field Public` or the tests need to use a different verification method (e.g., `ListTodos` returning empty). The plan must resolve this.

17. **LOW -- No test for concurrent/rapid sequential requests.** The plan uses `ThreadMode←0`, which eliminates true concurrency. However, the plan does not test or document what happens with rapid sequential requests (e.g., toggling and deleting the same todo in quick succession). With `ThreadMode←0` (effectively `ThreadMode←'DEBUG'` in the test runner per the Stark pattern at `/workspace/Stark/Tests/RunTests.apls` line 28), requests are serialised, so this is safe. But the plan should explicitly state this is covered by the threading choice.

18. **LOW -- No XSS integration test.** The architecture doc (line 281) specifies: "POST a todo with `<script>` in the title, verify the response contains escaped entities." The implementation plan has no integration test for this. The unit test `Test_TodoItemEscapedTitle` (line 102) covers the rendering layer, but there is no integration test that verifies the full round-trip (POST with malicious title, GET to verify escaped output).

## Open design decisions that must be resolved

1. **How is `staticRoot` resolved at runtime?** The plan says "Use `⎕NPARTS` for path resolution" but `⎕NPARTS` does not resolve relative paths. The implementer must choose between `(180⌶)`, `SALT_Data`, or hard-coding relative to the script location. This must be specified.

2. **How does the `/test/break` route get registered for OnErrorFn testing?** The plan does not specify where `BrokenHandler` lives, how it gets into the `Handlers` namespace, or how the route is added. The test harness needs a concrete mechanism.

3. **What does `FindTodo` return on error -- `⍬` or should it use `:Return` with no result?** The plan says "return `⍬`" but the calling pattern is not specified. Returning `⍬` from a function that normally returns an index requires the caller to check the type, which is fragile.

4. **Should `CreateTodo` return an error body (HTML fragment with message) on 400, or just call `req.Fail 400` and return empty?** The plan (line 232) shows `req.Fail 400` and "return" but does not specify what the return value is. Some tests (like `Test_CreateTodoMissingTitle`) only check `req.Response.Status`, but the `RespondHTML` pattern used elsewhere suggests an HTML error fragment should be returned. This affects the error response format.

5. **Are `todos` and `nextId` fields Public or Private?** Phase 4 unit tests directly access them (lines 196-197), which requires Public access. But exposing mutable internal state publicly is a design concern. The plan must decide and specify.

6. **What is the exact form of the `⎕VFI` validation?** As noted in issue 2, the plan's pattern fails on multi-token input. The implementer needs a specified, tested pattern.

## Architecture conformance check

1. **Project layout** -- PASS. Implementation plan's directory structure (lines 25-38) matches architecture doc (lines 25-42), including `Render/` as a directory-form namespace.

2. **Data model (id, title, completed)** -- PASS. Consistent between both documents. Implementation plan explicitly mentions `nextId` counter and no ID reuse.

3. **REST API (6 endpoints)** -- PASS. All six routes from the architecture doc table (lines 64-71) are registered across Phases 4-6.

4. **Static file serving via `⎕NGET`** -- PASS with gap. Both documents agree on `⎕NGET` with explicit routes. But the path construction detail (trailing separator) is missing from the implementation plan.

5. **`ThreadMode←0`** -- PASS. Implementation plan line 167 matches architecture doc line 58.

6. **`OnErrorFn` mechanism** -- PASS. Implementation plan Phase 4 (line 168) and Phase 7 match architecture doc section on error handling (lines 117-152).

7. **`RespondHTML` helper** -- PASS. Both documents describe the same dyadic helper with the same signature.

8. **HTML escaping** -- PASS. `Render.Escape` is specified in both documents with the same character set.

9. **Form-urlencoded unwrapping** -- PASS. Both documents mention `⊃req.Payload.title`.

10. **Path parameter validation via `⎕VFI`** -- PARTIAL FAIL. Architecture doc shows a specific code snippet (lines 98-104) that the implementation plan references, but the snippet has the multi-token bug (issue 2 above).

11. **`ContentTypeForFile` for static files** -- PASS. Both documents reference the Jarvis method. The Jarvis source (`/workspace/Stark/APLSource/Jarvis.aplc` line 1763-1768) confirms the method exists and works as described.

12. **`HandleError` signature** -- PARTIAL FAIL. Architecture doc handler list (line 215) says monadic; implementation plan (line 179) says dyadic. The dyadic form is correct per Stark source.

13. **`hx-swap="delete"` for delete operations** -- PASS. Architecture doc (line 177) and implementation plan (line 298) both use this pattern.

14. **OpenAPI inaccuracy noted** -- PASS. Both documents acknowledge this as a known cosmetic issue.

15. **Direct navigation to fragment endpoints** -- FAIL (not addressed in implementation plan). Architecture doc (lines 185-187) discusses the `HX-Request` header checking as a known trade-off. The implementation plan does not mention this at all, not even as an acknowledged limitation.

## Recommendations

1. **Provide a complete MockRequest implementation in Phase 1.** Include `SetContentType` and `ContentTypeForFile` methods with exact APL code. For `ContentTypeForFile`, hard-code a minimal lookup covering `html`, `css`, and `json` extensions. For `SetContentType`, append to `Response.Headers` matrix. Do not ask the implementer to reverse-engineer Jarvis internals.

2. **Fix the `⎕VFI` validation pattern.** Replace the architecture doc snippet with:
   ```apl
   (valid values)←⎕VFI req.PathParams.id
   :If 1≠≢valid
   :OrIf ~⊃valid
       req.Fail 400
       result←'' RespondHTML req
       :Return
   :EndIf
   id←⊃values
   ```
   This handles multi-token input and single invalid tokens.

3. **Specify `staticRoot` resolution explicitly.** Use the pattern from `⎕NPARTS` on the source file of the class, e.g.:
   ```apl
   dir←⊃1 ⎕NPARTS ⎕SRC_PATH  ⍝ or equivalent mechanism
   staticRoot←dir,'../static/'
   ```
   Or use `(⊃⎕CLASS ⎕THIS).SALT_Data.SourceFile` if available. Pick one and document it.

4. **Fix the `⎕NC` check for missing title.** Replace `9.1≠req.Payload.⎕NC⊂'title'` with `0=req.Payload.⎕NC⊂'title'`. Name class 9.1 is for namespace members; form field values are name class 2.1 (variables).

5. **Add a whitespace-only title test.** Add `Test_CreateTodoWhitespaceTitle` that POSTs `title=   ` (spaces only) and expects 400.

6. **Add an XSS integration test.** Add `Test_PostTodoXSSEscaped` that POSTs `title=<script>alert(1)</script>`, then GETs `/todos` and verifies the response contains `&lt;script&gt;`, not `<script>`.

7. **Specify `⎕DL` after server start in RunTests.apls.** Add `⎕DL 1` after `app.Start port` in the Phase 8 test runner description, matching the existing Stark test pattern.

8. **Make `todos` and `nextId` Public fields** (or provide accessor methods) so that unit tests can verify internal state. Document this as a pragmatic choice for testability.

9. **Specify the `/test/break` registration mechanism.** The simplest approach: add a public method `_RegisterTestRoutes` on TodoApp that registers `/test/break` pointing to a private `_BrokenHandler` method. The test runner calls this method after construction. This keeps the test route out of the production `Run.apls` path.

10. **Specify what `CreateTodo` and `FindTodo` return on error.** After `req.Fail`, each handler should return an HTML error fragment via `RespondHTML` (e.g., `result←'<div class="error">Title is required</div>' RespondHTML req`). This keeps the content-type consistent and gives htmx something to swap into the DOM.

11. **Add `⎕DL` or equivalent startup synchronisation to the integration test phase.** The plan should also specify how to detect that the server is ready (e.g., retry a health check GET to `/` with a short timeout).

## What the plan gets right

- The phased structure is sound. Each phase is independently verifiable, phases build on each other without circular dependencies, and the test-first approach is consistently applied.
- The test tables are concrete and specific. Each test has a clear assertion, making them implementable without ambiguity (apart from the issues noted above).
- The separation of Render functions from HTTP handlers is a good design that enables fast unit testing without a running server.
- The `RespondHTML` helper pattern correctly addresses the architecture review's concern about forgetting to set content-type.
- The error handling summary table (lines 427-434) is clear and complete, covering all error paths including the Stark default 404 for unknown routes.
- The `OnErrorFn` integration via Stark is correctly wired -- the plan matches the actual Stark source code for error handler invocation.
- The decision to use `ThreadMode←0` is appropriate and eliminates an entire class of concurrency bugs.
- The plan correctly identifies that `⎕NGET` with flag `0` returns a 3-element vector requiring `⊃` to extract content.
