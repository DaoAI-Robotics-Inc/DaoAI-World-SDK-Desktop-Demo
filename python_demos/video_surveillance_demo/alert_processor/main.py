#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import redis.asyncio as aioredis

# ===== Configuration =====
API_ENDPOINT       = os.getenv("API_SERVER", "http://192.168.10.101:38080")
REDIS_SERVER_URL   = os.getenv(
    "REDIS_SERVER",
    "redis://default:mypassword@192.168.10.101:16379/0"
)
GET_ENDPOINT       = "/cameras"
INTRO_WORKFLOW_ID  = 9
RUN_WORKFLOW_ID    = 8
TARGET_NODE_ID     = "5b80ef63-41ec-4300-8b37-e7781246f9f2"
LIMIT              = 200
# ======================

async def fetch_all_cameras(session: aiohttp.ClientSession) -> list:
    """
    分页异步获取所有 camera 列表。
    """
    cameras = []
    offset = 0
    while True:
        params = {"offset": offset, "limit": LIMIT}
        async with session.get(f"{API_ENDPOINT}{GET_ENDPOINT}", params=params) as resp:
            resp.raise_for_status()
            batch = await resp.json()
        if not batch:
            break
        cameras.extend(batch)
        if len(batch) < LIMIT:
            break
        offset += LIMIT
    return cameras

async def list_target_cameras(session: aiohttp.ClientSession, workflow_id: int) -> list[int]:
    """
    在所有摄像头中筛选出 workflow_id 匹配的 camera ID 列表。
    """
    all_cams = await fetch_all_cameras(session)
    return [
        c.get("id") or c.get("camera_id")
        for c in all_cams
        if c.get("workflow_id") == workflow_id
    ]

async def get_latest_camera_frame(redis_client: aioredis.Redis, camera_id: int) -> bytes | None:
    """
    从 Redis 中获取某 camera 最新一帧的 image_data（bytes）。
    """
    pattern = f"camera:{camera_id}:frame:*"
    keys = await redis_client.keys(pattern)
    if not keys:
        return None
    timestamps = [int(k.split(b":")[-1]) for k in keys]
    latest = max(timestamps)
    key = f"camera:{camera_id}:frame:{latest}"
    return await redis_client.hget(key, "image_data")

async def run_workflow(
    session: aiohttp.ClientSession,
    input_image: bytes,
    workflow_id: int,
    target_node_id: str | None = None
) -> dict:
    """
    异步调用 /workflows/{workflow_id}/run 并返回解析后的 JSON 结果。
    """
    url = f"{API_ENDPOINT}/workflows/{RUN_WORKFLOW_ID}/run"
    form = aiohttp.FormData()
    form.add_field("input_image", input_image, filename="image.jpg", content_type="image/jpeg")
    params = {"target_node_id": target_node_id} if target_node_id else None
    async with session.post(url, data=form, params=params) as resp:
        resp.raise_for_status()
        print(resp)
        return await resp.json()

async def main():
    # 初始化异步 Redis 客户端
    redis_client = aioredis.from_url(REDIS_SERVER_URL, decode_responses=False)

    timeout = aiohttp.ClientTimeout(total=None)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 1) 列出 target cameras
        camera_ids = await list_target_cameras(session, INTRO_WORKFLOW_ID)
        print(f"Found {len(camera_ids)} cameras for workflow {INTRO_WORKFLOW_ID}: {camera_ids}\n")

        # 2) 轮流处理每个 camera
        for cam_id in camera_ids:
            print(f"Camera {cam_id}:")
            frame = await get_latest_camera_frame(redis_client, cam_id)
            if not frame:
                print("  No frame data in Redis, skipping\n")
                continue

            try:
                result = await run_workflow(session, frame, INTRO_WORKFLOW_ID, TARGET_NODE_ID)
                print(f"  测试4: 车流量统计 | Camera {cam_id} → result: {result}\n")
            except Exception as e:
                print(f"  Workflow call failed: {e}\n")

    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())
