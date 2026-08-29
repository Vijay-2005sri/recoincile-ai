from streamlit.testing.v1 import AppTest


def test_bundled_demo_reconciles_in_streamlit():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.button[2].click().run()
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Records processed"] == "180"
    assert metrics["Measured accuracy"] == "100.0%"
    explanation_button = next(button for button in app.button if button.label == "Generate safe explanation")
    explanation_button.click().run()
    assert not app.exception
    assert any("deterministic fallback" in message.value.lower() for message in app.info)
