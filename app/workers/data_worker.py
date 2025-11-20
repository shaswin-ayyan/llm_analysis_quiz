import pandas as pd
import httpx
from io import StringIO
import logging

logger = logging.getLogger("uvicorn.error")


class DataWorker:
    async def load_csv(self, url: str) -> pd.DataFrame:
        logger.info(f"Downloading CSV from {url}")
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            r.raise_for_status()
            return pd.read_csv(StringIO(r.text))

    def compute_region_correlations(self, df: pd.DataFrame):
        """
        Computes Pearson correlation between Marketing_Spend_USD and
        Net_Revenue_USD for each region.
        Returns: {region_name: correlation_value}
        """
        results = {}
        for region, group in df.groupby("Region"):
            try:
                corr = group["Marketing_Spend_USD"].corr(
                    group["Net_Revenue_USD"]
                )
                results[region] = corr
            except Exception as e:
                logger.error(f"Correlation failed for region {region}: {e}")
        return results

    def get_strongest_positive_region(self, df: pd.DataFrame):
        result = self.compute_region_correlations(df)
        if not result:
            return None

        # Sort by correlation strength (descending)
        strongest = max(result.items(), key=lambda x: x[1])
        region, corr_value = strongest
        return region, corr_value
