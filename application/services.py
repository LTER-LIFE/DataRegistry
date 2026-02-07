import asyncio
import logging
import httpx
from flask import config
from config import Config


class LlmMetadataService:
    def __init__(self):
        self.api_key = Config.LLM_API_KEY
        self.base_url = Config.LLM_SERVICE_URL
        self.llm_model = Config.LLM_MODEL

    async def get_metadata(self, target_url, timeout=300):
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            # 1. Submit the job
            submit_res = await client.post(
                f"{self.base_url}/jobs/",
                json={"model": self.llm_model, "url": target_url},
                headers=headers
            )
            submit_res.raise_for_status()
            job_id = submit_res.json().get("job_id")

            # 2. Poll for the result
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                status_res = await client.get(f"{self.base_url}/jobs/{job_id}", headers=headers)
                status_res.raise_for_status()
                data = status_res.json()

                status = data.get("status")

                if status == "success":
                    logging.info(f"Job {job_id} completed successfully.")
                    data_res = await client.get(f"{self.base_url}/jobs/{job_id}/result", headers=headers)
                    data_res.raise_for_status()
                    data = data_res.json()
                    return data

                if status.find("fail") > -1:
                    raise Exception(f"AI Job failed: {data.get('error')}")

                # If "pending" or "queued", we just wait
                logging.info(f"Job {job_id} is {status}...")
                await asyncio.sleep(2)  # Non-blocking sleep

            raise Exception("Timed out waiting for AI metadata.")
