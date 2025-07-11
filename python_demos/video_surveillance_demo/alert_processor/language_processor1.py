#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import redis.asyncio as aioredis
import time
import json

# ===== Configuration =====
API_ENDPOINT        = os.getenv("API_SERVER", "http://s1.daoai.ca:38080")
REDIS_SERVER_URL    = os.getenv(
    "REDIS_SERVER",
    "redis://default:mypassword@s1.daoai.ca:16379/0"
)
GET_CAMERAS_PATH    = "/cameras"
INTRO_WORKFLOW_ID   = 53
RUN_WORKFLOW_ID     = 54
TARGET_NODE_ID      = None  # "5b80ef63-41ec-4300-8b37-e7781246f9f2"
LIMIT               = 200
LOOP_INTERVAL_SEC   = 1.0

CONDITION_1_ID = "f71b7c2b-d447-445b-b021-a7dc44df0d2a"
CONDITION_2_ID = "430f7997-6b16-4fb9-8e67-149c15002617"
VIS_1_ID = "9af08c79-ab2f-4719-b064-adc924101404"
VIS_2_ID = "391973f6-fd49-41eb-8383-2f0b587d627c"

# When True, save the JSON result of each run to SAMPLE_JSON_PATH
SAVE_SAMPLE_RESULT  = True
SAMPLE_JSON_PATH    = "sample.json"
# ======================

async def fetch_all_cameras(session: aiohttp.ClientSession) -> list:
    """
    分页异步获取所有 camera 列表。
    """
    cameras = []
    offset = 0
    while True:
        params = {"offset": offset, "limit": LIMIT}
        url = f"{API_ENDPOINT}{GET_CAMERAS_PATH}"
        async with session.get(url, params=params) as resp:
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

async def get_latest_camera_frame(
    redis_client: aioredis.Redis,
    camera_id: int,
    max_wait: float = 0.2,
    poll_interval: float = 0.05
) -> bytes | None:
    """
    从 Redis 中获取某 camera 最新一帧的 image_data（bytes），
    最多等待 max_wait 秒，轮询 poll_interval 秒。
    """
    pattern = f"camera:{camera_id}:frame:*"
    start = time.monotonic()
    while True:
        keys = await redis_client.keys(pattern)
        if keys:
            timestamps = [int(k.split(b":")[-1]) for k in keys]
            latest = max(timestamps)
            key = f"camera:{camera_id}:frame:{latest}"
            data = await redis_client.hget(key, "image_data")
            if data:
                return data
        if time.monotonic() - start > max_wait:
            return None
        await asyncio.sleep(poll_interval)

async def run_workflow(
    session: aiohttp.ClientSession,
    input_image: bytes,
    workflow_id: int,
    target_node_id: str | None = None
) -> dict:
    """
    异步调用 /workflows/{workflow_id}/run 并返回解析后的 JSON 结果。
    """
    url = f"{API_ENDPOINT}/workflows/{workflow_id}/run"
    form = aiohttp.FormData()
    form.add_field("input_image", input_image, filename="image.jpg", content_type="image/jpeg")
    params = {"target_node_id": target_node_id} if target_node_id else None
    async with session.post(url, data=form, params=params) as resp:
        resp.raise_for_status()
        return await resp.json()

async def main():
    # 初始化异步 Redis 客户端
    redis_client = aioredis.from_url(REDIS_SERVER_URL, decode_responses=False)
    timeout = aiohttp.ClientTimeout(total=None)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # 获取所有属于 INTRO_WORKFLOW_ID 的摄像头
        while True:
            camera_ids = await list_target_cameras(session, INTRO_WORKFLOW_ID)
            print(f"Found {len(camera_ids)} cameras for workflow {INTRO_WORKFLOW_ID}: {camera_ids}\n")

            for cam_id in camera_ids:
                print(f"Camera {cam_id}:")
                frame = await get_latest_camera_frame(redis_client, cam_id)
                if not frame:
                    print("  No frame data in Redis, skipping\n")
                    continue

                try:
                    result = await run_workflow(session, frame, RUN_WORKFLOW_ID, TARGET_NODE_ID)
                    print(f"  测试4: 车流量统计 | Camera {cam_id} → result: {result}\n")

                    # 根据常量保存 sample.json
                    if SAVE_SAMPLE_RESULT:
                        with open(SAMPLE_JSON_PATH, "w", encoding="utf-8") as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        print(f"  Saved workflow result to {SAMPLE_JSON_PATH}\n")

                except Exception as e:
                    print(f"  Workflow call failed: {e}\n")

            # 循环间隔
            await asyncio.sleep(LOOP_INTERVAL_SEC)

    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())

