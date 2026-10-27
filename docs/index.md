---
hide:
  - navigation
  - toc
---

<div class="dx-home" markdown>

<div class="dx-hero" markdown>
<div class="dx-hero__copy" markdown>

<p class="dx-eyebrow">OPEN SOURCE DOCUMENT PROCESSING</p>

# Many arms.<br> One API.

<p class="dx-lead">Your documents, ready for what’s next.</p>
<p class="dx-description">Turn PDFs, Office files, and scans into structured, LLM-ready data. One self-hosted gateway. The right engine for the job.</p>

<div class="dx-actions" markdown>

[Get started :octicons-arrow-right-24:](installation.md){ .md-button .md-button--primary aria-label="Get started" }
[Explore the docs](quickstart.md){ .md-button }

</div>

<p class="dx-meta">Python 3.12 <span aria-hidden="true">/</span> Self-hosted <span aria-hidden="true">/</span> MIT licensed</p>

</div>
<div class="dx-example" markdown>

<div class="dx-example__header"><span>LESS GLUE. MORE BUILDING.</span><span>Python</span></div>

```python
import doctopus

# A document in. Structured data out.
doc = doctopus.parse("paper.pdf")

print(doc.markdown)
print(doc.tables)
print(doc.processing.backend)

# Ready for your retrieval pipeline.
chunks = doctopus.chunk("paper.pdf")
```

<div class="dx-example__footer"><span class="dx-status" aria-hidden="true"></span>One consistent Document schema.</div>

</div>
</div>

<div class="dx-overview" markdown>
<div><strong>8</strong><span>processing engines</span></div>
<div><strong>4</strong><span>ways to connect</span></div>
<div><strong>1</strong><span>consistent schema</span></div>

[Meet the engines ↗](concepts/engines.md)

</div>

<div class="dx-section-heading" markdown>

<p class="dx-eyebrow">A SMALLER STACK</p>

## Everything you need.<br> Less to wire together.

</div>

<div class="dx-features" markdown>
<div class="dx-feature" markdown>

<span class="dx-feature__number">01 / ROUTING</span>

### The right engine, explained.

Start with lightweight Xberg. Add engines as you need them. The router selects by format, mode, and available memory, and records why.

[How routing works :octicons-arrow-right-24:](concepts/routing.md){ aria-label="How routing works" }

</div>
<div class="dx-feature" markdown>

<span class="dx-feature__number">02 / STRUCTURE</span>

### Different inputs. Same shape.

Get Markdown, text, tables, and structured blocks through one versioned schema. Export heading-aware chunks that keep tables intact.

[Explore the output :octicons-arrow-right-24:](concepts/output.md){ aria-label="Explore the output" }

</div>
<div class="dx-feature" markdown>

<span class="dx-feature__number">03 / CONTROL</span>

### Your infrastructure. Your call.

Run locally or deploy with Docker. Choose your engines and connect through Python, the command line, REST, or an MCP client.

[Deploy Doctopus :octicons-arrow-right-24:](deployment.md){ aria-label="Deploy Doctopus" }

</div>
</div>

<div class="dx-workflow" markdown>
<div class="dx-workflow__intro" markdown>

<p class="dx-eyebrow">FITS YOUR WORKFLOW</p>

## Start small.<br> Build from here.

Install the package, parse a document, and put the output to work. Use the same gateway from your terminal, application, or agent.

[Read the quick start :octicons-arrow-right-24:](quickstart.md){ aria-label="Read the quick start" }

<p class="dx-note">OCR and layout engines may download model weights on first use.</p>

</div>
<div class="dx-workflow__code" markdown>

=== "CLI"

    ```bash
    pip install doctopus-ai
    doctopus parse paper.pdf

    # Return structured output
    doctopus parse paper.pdf --format json

    # Build a retrieval corpus
    doctopus chunk ./corpus --output corpus.jsonl
    ```

=== "Python"

    ```python
    import doctopus

    doc = doctopus.parse("paper.pdf")
    print(doc.markdown)
    print(doc.processing.decision.reasons)

    chunks = doctopus.chunk(
        "paper.pdf", max_chars=1500
    )
    ```

=== "REST"

    ```bash
    # Start the API and drag-and-drop demo
    doctopus serve --port 8000

    # Parse a document
    curl -F file=@paper.pdf \
      http://localhost:8000/v1/parse
    ```

=== "MCP"

    ```json
    {
      "mcpServers": {
        "doctopus": {
          "command": "doctopus",
          "args": ["mcp", "--root", "/path/to/docs"]
        }
      }
    }
    ```

</div>
</div>

<div class="dx-pipeline" markdown>

<p class="dx-eyebrow">UNDER THE HOOD</p>

## A clear path from file to data.

<ol class="dx-steps">
<li><span>01</span><strong>Inspect</strong><p>Read the format, size, and available resources.</p></li>
<li><span>02</span><strong>Route</strong><p>Choose an available engine for the job.</p></li>
<li><span>03</span><strong>Extract</strong><p>Parse content, with at most one fallback when needed.</p></li>
<li><span>04</span><strong>Build</strong><p>Return a document with content and processing details.</p></li>
</ol>

</div>

<div class="dx-closing" markdown>
<div markdown>

### Make your first document useful.

A couple of commands is a good place to start.

</div>

[Get started :octicons-arrow-right-24:](installation.md){ .md-button .md-button--primary aria-label="Get started" }

</div>

<p class="dx-license" markdown>Doctopus is [MIT licensed](https://github.com/adityasasidhar/doctopus/blob/main/LICENSE). Backend packages and model weights have their own licenses.</p>

</div>
