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
        "local ai tools"
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


def test_license_filter_rejects_unknown_and_noncommercial_commons_assets():
    assert retrieval._license_is_usable({
        "provider": "pixabay", "license": "Pixabay Content License"
    })
    assert retrieval._license_is_usable({
        "provider": "wikimedia_commons", "license": "CC BY 4.0"
    })
    assert not retrieval._license_is_usable({
        "provider": "wikimedia_commons", "license": "License not identified"
    })
    assert not retrieval._license_is_usable({
        "provider": "wikimedia_commons", "license": "CC BY-NC 4.0"
    })


def test_dynamic_visuals_are_never_product_evidence():
    # The manifest contract is explicit: these are generic supporting images,
    # not authenticated software-interface captures.
    assert "non-evidence" in retrieval.prepare_dynamic_scene_visuals.__doc__


def test_pixabay_video_search_maps_metadata_and_caches(tmp_path, monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"hits": [{
                "id": 42, "pageURL": "https://pixabay.com/videos/demo-42/",
                "tags": "freelancer office", "user": "creator",
                "duration": 12, "videos": {
                    "medium": {"url": "https://cdn.pixabay.com/video/demo.mp4",
                              "width": 1280, "height": 720}
                }
            }]}

    monkeypatch.setattr(retrieval.requests, "get", lambda *a, **k: Response())
    items = retrieval._pixabay_video_search("freelancer office", tmp_path, "test-key")
    assert items[0]["provider"] == "pixabay_video"
    assert items[0]["asset_id"] == "42"
    assert items[0]["video_url"].endswith("demo.mp4")
    assert items[0]["license"] == "Pixabay Content License"
    # A second lookup uses the cache and makes no network call.
    monkeypatch.setattr(
        retrieval.requests, "get",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("cache miss")),
    )
    assert retrieval._pixabay_video_search("freelancer office", tmp_path, "test-key") == items


def test_video_download_rejects_untrusted_hosts(tmp_path):
    candidate = {"video_url": "https://example.invalid/video.mp4"}
    assert retrieval._download_video(candidate, tmp_path / "clip.mp4") is None
    assert not (tmp_path / "clip.mp4").exists()


def test_video_candidates_win_relevance_ties():
    query = "freelancer office"
    image = {"provider": "pixabay", "title": query, "tags": query}
    video = {"provider": "pixabay_video", "title": query, "tags": query, "video_url": "https://cdn.pixabay.com/v.mp4"}
    ordered = sorted(
        [image, video],
        key=lambda item: (-retrieval._candidate_score(query, item),
                          0 if item.get("video_url") else 1,
                          item.get("provider", "")),
    )
    assert ordered[0] is video

def test_commons_video_search_preserves_license_and_source_metadata(tmp_path, monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"query": {"pages": {"123": {
                "pageid": 123, "title": "File:Business meeting.webm",
                "imageinfo": [{
                    "url": "https://upload.wikimedia.org/wikipedia/commons/demo.webm",
                    "descriptionurl": "https://commons.wikimedia.org/wiki/File:Business_meeting.webm",
                    "width": 1280, "height": 720,
                    "extmetadata": {
                        "LicenseShortName": {"value": "CC BY 4.0"},
                        "Artist": {"value": "Test creator"},
                    }
                }]
            }}}}
    monkeypatch.setattr(retrieval.requests, "get", lambda *a, **k: Response())
    items = retrieval._commons_video_search("business meeting", tmp_path)
    assert items[0]["provider"] == "wikimedia_commons_video"
    assert items[0]["video_url"].endswith(".webm")
    assert items[0]["license"] == "CC BY 4.0"
    assert retrieval._license_is_usable(items[0])
