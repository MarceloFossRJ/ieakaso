# Agent Profile

## 1. Core Identity & Role
You are an expert Python developer assistant. Your goal is to help build a clean, maintainable, and well-tested Python application from scratch using `uv`.

## 2. Basic rules
* **Write the most simple implementation that works.**
* **No abstractions that weren't explicitly requested.**
* **Deletion over addition. Boring over clever. Fewest files possible.**
* **Mark deliberate simplifications that cut a real corner with a known ceiling (global lock, O(n²) scan, naive heuristic) with a ponytail: comment naming the ceiling and upgrade path.**

## 3. Technical Stack (DRY - Single Source of Truth)
* **Language:** Python 3.13
* **Project & Dependency Management:** `uv` (Astral)
* **Data Validation & Settings:** `pydantic` 
* **Environment Configuration:** `python-dotenv`
* **Testing Frameworks:** `pytest` (TDD / Unit testing)
* **Code Quality & Static Analysis:** `ruff` (fast style checks) and `prospector` (deep code analytics)
* **LLM model:** `openai:gpt-5.4`

## 4. Testing Strategy (TDD)

### TDD (Test-Driven Development) — Code-Centric Approach
* **Focus:** Code correctness, edge cases, and structural integrity at the unit level.
* **When to use:** Pure functions, utility modules, mathematical calculations, and Pydantic data transformations.
* **Workflow:** Write a failing unit test in `pytest`, implement the minimal code to make it pass (KISS), and refactor.

## 5. Development Guardrails (KISS & YAGNI)

### Keep It Simple (KISS)
* **Flat Over Nested:** Favor flat directory layouts and simple module structures over deep package hierarchies.
* **Standard Library & Modern Idioms:** 
  * Use `pathlib` for all path management. Do **NOT** use `os.path`.
  * Prefer f-strings over `str.format()` or `%` formatting for string interpolation.
* **Pythonic Code (EAFP):** Follow the **EAFP** (Easier to Ask for Forgiveness than Permission) principle. Handle exceptions using `try/except` blocks rather than checking conditions or states upfront with `if` statements.
* **Type Hinting:** Explicitly type-hint all public functions and methods, including their return types (e.g., `def calculate_total(price: float) -> float:`).
* **Documentation:** Write **Google-style docstrings** for every public function, class, and method.
* **Use Pydantic model for structured data**: the boundary types (model output, persisted records) and the internal objects passed between modules alike.
* **Explicit Environment Initialization:** Always load environment variables using explicit `load_dotenv()` initializations inside entry points.

### You Aren't Gonna Need It (YAGNI)
* **No Premature Abstraction:** Write functions and concrete classes first. Do not design abstract interfaces until we have at least three distinct implementations requiring them.
* **Active Requirements Only:** Only implement features or helper functions that satisfy the immediate task. 
* **Never Commit Secrets:** Do not hardcode secrets. Ensure instructions always direct the user to write credentials to a `.env` file, and keep `.env` inside `.gitignore`.

## 6. Workflow Strategy
1. **Test Baseline:** For any new block of work, determine if it requires a BDD feature file (business requirement) or a direct TDD unit test (technical implementation) first.
2. **Incremental Delivery:** Provide small, functional, and testable code snippets.
3. **Refactoring Rule:** Only apply DRY principles to refactor code when logic is repeated **three times** (Rule of Three). 

## 7. Quality Tools & Commands (KISS / DRY)
Utilize the `uv` ecosystem exclusively.

* **Add dev dependencies:** `uv add --dev ruff pytest pytest-bdd "prospector[with_everything]"`
* **Run Style Linter/Formatter:** `uv run ruff check . --fix && uv run ruff format .`
* **Run Deep Static Analysis:** `uv run prospector`
* **Run All Tests:** `uv run pytest`

# Project
A small prototype that turns patient documents into a structured patient record.

## Goal
* understand your technical judgement 
* understand how you would lead a team from a prototype to a dependable product.

## Scope
*Local file persistence and a readable CLI report are sufficient

## Out of Scope
* UI, deployment, OCR, FHIR integration or production infrastructure is not required. 
* Specialist oncology knowledge is not required.
* Extract documented facts without inferring treatment recommendations.

## Requirements
* The `data` directory contains three variants of a synthetic patient. 
* Treat each patient directory as a separate case, even where documents or demographics look identical. 
* Adapt the schema to represent:
  * Name and birthday.
  * Clinical diagnoses and procedures.
  * Source evidence for extracted information.
  * Conflicting or unknown information.
* Idempotent extraction: repeated extraction must not accumulate duplicate records or corrupt results. If a run fails or remains incomplete, make that visible. Explain your rerun and failure behaviour; a comprehensive retry framework is not required.
* Database: persisting to disk is sufficient.

## Business Context

### Conflicts and uncertainty

Documents can disagree. Keep material competing claims and their evidence visible in both the data model and report. Explain any proposed resolution and distinguish it from an unresolved conflict. Some conflicts cannot be resolved until a clinician obtains further information.
Missing information must remain identifiable as unknown. Use your judgement about how to model these states.

### Citations
Clinicians need to be able to check extracted information against the original documents. For clinical facts and identifying information, preserve an exact source excerpt and a locator that lets a reviewer find the relevant passage in its source document. Choose a suitable granularity, such as a section or line range.
Make the relationship between each extracted value and its evidence clear in the report, including evidence for conflicting claims.

### Validation
Include a few focused, runnable checks or tests covering conflict preservation, source evidence and repeated execution. Document the test command. You may use recorded or mocked model responses for repeatable tests. Include a sample result/report from a real extraction run on the supplied synthetic documents where access permits it.
Document important gaps within the time limit. We may also check small variations of the synthetic inputs using the same format and requirements.