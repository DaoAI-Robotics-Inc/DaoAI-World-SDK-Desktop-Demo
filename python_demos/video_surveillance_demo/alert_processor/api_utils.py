import os

import requests

API_ENDPOINT = os.getenv("API_SERVER", "http://localhost:38080")


def run_workflow(
    input_image: bytes, workflow_id: int, target_node_id: str | None = None
) -> requests.Response:
    files = {"input_image": ("image.jpg", input_image, "image/jpeg")}
    params = {"target_node_id": target_node_id} if target_node_id else None
    return requests.post(
        API_ENDPOINT + f"/workflows/{workflow_id}/run", files=files, params=params
    )


if __name__ == "__main__":
    with open("test.jpg", "rb") as f:
        image_data = f.read()
    response = run_workflow(image_data, 5)
    print(response.json())
