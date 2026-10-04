from contexta_mcp.chunker import parse


def test_h1_service_name_extracted():
    md = "# KNOWLEDGE: order-api\n\n## Business context\n### Why\nSells things.\n"
    p = parse(md)
    assert p.service_name == "order-api"


def test_h1_template_stub_is_ignored():
    md = "# KNOWLEDGE: <SERVICE_NAME>\n\n## Business context\n### Why\nx\n"
    assert parse(md).service_name is None


def test_one_chunk_per_h3():
    md = (
        "# KNOWLEDGE: svc\n"
        "## Business context\n"
        "### Why\nIt exists.\n"
        "### Who\nUsers.\n"
        "## Operational context\n"
        "### On-call\nTeam A.\n"
    )
    p = parse(md)
    assert [(c.section, c.subsection, c.text) for c in p.chunks] == [
        ("Business context", "Why", "It exists."),
        ("Business context", "Who", "Users."),
        ("Operational context", "On-call", "Team A."),
    ]
    assert p.skipped == 0


def test_tbd_subsections_are_skipped():
    md = (
        "# KNOWLEDGE: svc\n"
        "## Business context\n"
        "### Why\n_TBD_\n"
        "### Who\nUsers.\n"
    )
    p = parse(md)
    assert len(p.chunks) == 1
    assert p.chunks[0].subsection == "Who"
    assert p.skipped == 1


def test_na_subsections_are_skipped():
    md = (
        "# KNOWLEDGE: svc\n"
        "## Operational context\n"
        "### On-call\nN/A — single-person service\n"
        "### Deployment\nk8s prod-eu.\n"
    )
    p = parse(md)
    assert [c.subsection for c in p.chunks] == ["Deployment"]
    assert p.skipped == 1


def test_wip_subsections_are_skipped():
    md = (
        "# KNOWLEDGE: svc\n"
        "## Lifecycle and status\n"
        "### Known tech debt\n_WIP_\n"
        "### Maturity\nstable\n"
    )
    p = parse(md)
    assert [c.subsection for c in p.chunks] == ["Maturity"]
    assert p.skipped == 1


def test_html_comments_stripped_when_assessing_placeholder():
    md = (
        "# KNOWLEDGE: svc\n"
        "## Business context\n"
        "### Why\n<!-- hint -->\n_TBD_\n"
    )
    p = parse(md)
    assert p.chunks == []
    assert p.skipped == 1


def test_h2_inside_code_fence_is_not_a_section():
    md = (
        "# KNOWLEDGE: svc\n"
        "## Architecture patterns and decisions\n"
        "### Patterns in use\n"
        "Example config:\n\n"
        "```yaml\n"
        "## not a heading\n"
        "foo: bar\n"
        "```\n"
        "After the fence.\n"
    )
    p = parse(md)
    assert len(p.chunks) == 1
    assert p.chunks[0].subsection == "Patterns in use"
    assert "## not a heading" in p.chunks[0].text


def test_body_without_subsection_is_not_a_chunk():
    md = (
        "# KNOWLEDGE: svc\n"
        "## Business context\n"
        "preamble prose with no H3 after it\n"
        "### Why\nreal body\n"
    )
    p = parse(md)
    assert [c.subsection for c in p.chunks] == ["Why"]