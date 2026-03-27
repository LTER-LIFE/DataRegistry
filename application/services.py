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

    async def submit_job(self, target_url):
        """Submit a job to the LLM service. Returns the job_id."""
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/jobs/",
                json={"model": self.llm_model, "url": target_url},
                headers=headers
            )
            res.raise_for_status()
            return res.json().get("job_id")

    async def check_job(self, job_id):
        """
        Perform a single status check for a job.
        Returns (status, result_data_or_none).
        result_data is only populated when status == 'success'.
        """
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.base_url}/jobs/{job_id}", headers=headers)
            res.raise_for_status()
            data = res.json()
            status = data.get("status")

            if status == "success":
                logging.info(f"Job {job_id} completed successfully.")
                result_res = await client.get(f"{self.base_url}/jobs/{job_id}/result", headers=headers)
                result_res.raise_for_status()
                return status, result_res.json()

            return status, None

    async def get_metadata(self, target_url, timeout=300):
        job_id = await self.submit_job(target_url)

        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            status, data = await self.check_job(job_id)

            if status == "success":
                return data

            if status.find("fail") > -1:
                raise Exception(f"AI Job failed.")

            logging.info(f"Job {job_id} is {status}...")
            await asyncio.sleep(2)

        raise Exception("Timed out waiting for AI metadata.")
