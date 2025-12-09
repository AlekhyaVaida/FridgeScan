from app.infer_spoilage import classify_image

def test_classify_image():
    label, loss = classify_image("data/test/freshapple.jpg", threshold=0.01)
    assert label in ["fresh", "spoiled"]
    assert isinstance(loss, float)
