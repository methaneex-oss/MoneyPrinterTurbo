from app.services import solo_stack_visual_retrieval as retrieval


def test_build_scene_queries_tracks_distinct_script_scenes():
    queries = retrieval.build_scene_queries(
        "Claude Code vs llama.cpp",
        "Claude Code can inspect and edit a repository. "
        "llama.cpp runs quantized models locally. "
        "Compare latency, memory use, and workflow trade-offs.",
        terms=["Claude Code interface", "llama.cpp terminal"],
        limit=4,
    )
    assert len(queries) == 4
    assert "claude code" in queries[0].casefold()
    assert "llama.cpp" in queries[1].casefold()
    assert len({query.casefold() for query in queries}) == len(queries)


def test_build_scene_queries_has_bounded_fallback():
    assert retrieval.build_scene_queries("Local AI tools", "", limit=20) == [
        "Local AI tools"
    ]


def test_candidate_score_prefers_relevant_visual_metadata():
    query = "llama.cpp local model inference terminal"
    relevant = {
        "title": "llama.cpp local model inference",
        "tags": "terminal, quantized model",
        "source_url": "",
    }
    generic = {
        "title": "Person using laptop",
        "tags": "office, computer",
        "source_url": "",
    }
    assert retrieval._candidate_score(query, relevant) > retrieval._candidate_score(
        query, generic
    )


def test_dynamic_download_rejects_untrusted_hosts(tmp_path):
    candidate = {"image_url": "https://example.com/fake.png"}
    assert retrieval._download_image(candidate, tmp_path / "image.png") is None
    assert not (tmp_path / "image.png").exists()


def test_dynamic_download_rejects_credentials_even_on_allowed_host(tmp_path):
    candidate = {
        "image_url": "https://untrusted@cdn.pixabay.com/image.jpg"
    }
    assert retrieval._download_image(candidate, tmp_path / "image.png") is None


def test_cache_expires_and_round_trips(tmp_path, monkeypatch):
    cache = retrieval._cache_path(tmp_path, "llama.cpp local inference", "commons")
    retrieval._write_cache(cache, [{"title": "llama.cpp"}])
    assert retrieval._read_cache(cache) == [{"title": "llama.cpp"}]

    monkeypatch.setattr(retrieval.time, "time", lambda: 10**12)
    assert retrieval._read_cache(cache) is None


def test_dynamic_visuals_are_never_product_evidence():
    # The manifest contract is explicit: these are generic supporting images,
    # not authenticated software-interface captures.
    assert "is_product_evidence" in retrieval.prepare_dynamic_scene_visuals.__doc__
    assert (
        "is_product_evidence=false"
        in retrieval.prepare_dynamic_scene_visuals.__doc__
    )
