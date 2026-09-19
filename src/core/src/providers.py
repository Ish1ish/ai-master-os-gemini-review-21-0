def fake_model_provider(prompt):
    return {"provider":"o23-test-provider","text":"TEST_MODEL_RESPONSE","prompt_chars":len(prompt)}

def fake_search_provider(query):
    return {"results":[
        {"title":"O23 Evidence A","url":"https://example.org/o23/a",
         "snippet":f"Evidence for {query}: customers report recurring onboarding friction.",
         "published_at":"2026-08-22","authority":"Example Research","source_type":"web"},
        {"title":"O23 Evidence B","url":"https://example.org/o23/b",
         "snippet":f"Evidence for {query}: current alternatives still have setup complexity.",
         "published_at":"2026-08-23","authority":"Example Research","source_type":"web"}]}
