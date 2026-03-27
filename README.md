# Todo Application

A classic todo application with an [htmx](https://htmx.org/) front-end and a [Dyalog APL](https://www.dyalog.com/) back-end, using the [Stark](Stark/) REST router on top of Jarvis.

## Overview

The server returns HTML fragments rather than JSON. htmx swaps these fragments into the DOM, giving a responsive single-page experience with no client-side JavaScript beyond htmx itself.

- **Stark** provides declarative route registration and path-parameter extraction.
- **Jarvis** handles HTTP, TCP/IP, and response serialisation.
- Static assets (HTML, CSS) are served from disk via explicit routes using `⎕NGET`.
- All user input is HTML-escaped server-side to prevent XSS.
- Centralised error handling via Stark's `OnErrorFn` mechanism.

## Running

```bash
dyalogscript Run.apls
```

Opens on `http://localhost:8080` by default.

## Testing

```bash
dyalogscript RunTests.apls
```

Runs the full unit and integration test suite.

## Project structure

```
APLSource/
  TodoApp.aplc          -- application class (routes, handlers, data model)
  Render/               -- HTML rendering functions (Escape, TodoItem, TodoList, RespondHTML)
static/
  index.html            -- shell page (loads htmx from CDN)
  style.css             -- minimal styling
Stark/                  -- Stark REST router (dependency)
tests/
  Unit/                 -- unit tests (rendering, data operations)
  Integration/          -- HTTP-level tests via HttpCommand
Run.apls                -- production entry point
RunTests.apls           -- test runner
```

## Documentation

- [Architecture plan](docs/plans/architecture.md)
- [Implementation plan](docs/plans/implementation.md)
- [Architecture review](docs/reviews/architecture.md)
- [Implementation review](docs/reviews/implementation.md)

## Requirements

- Dyalog APL 20.0+

## Licence

[MIT](LICENCE)
