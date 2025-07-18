from datetime import datetime
from typing import List, Optional
from prometheus_api_client import PrometheusConnect

from src.modules.inventory.db import Instance


class Prometheus:
    def __init__(
        self,
        prometheus_url: str,
        manager_api_address: Optional[str] = None
    ):
        self.prometheus = PrometheusConnect(url=prometheus_url)
        if not self.prometheus.check_prometheus_connection():
            raise Exception("Could not connect to Prometheus")
        self.manager_api_address = manager_api_address

    def get_scrape_targets(self, instances: List[Instance]) -> List[dict]:
        targets = []
        for instance in instances:
            instance_id = str(instance.id)
            targets.append({
                "targets": [self.manager_api_address],
                "labels": {
                    "job": "instances",
                    "instance_id": instance_id,
                    "__metrics_path__": f"/metrics/instances/{instance_id}"
                }

            })

        return targets

    def get_free_space(self, instance_id: str):
        def bytes_to_gb(bytes_value):
            return round(int(bytes_value) / (1024 ** 3), 2)

        def calculate_percentages(free_gb, total_gb):
            if total_gb <= 0:
                return 0, 0, 0
            free_pct = round((free_gb / total_gb) * 100, 2)
            used_gb = round(total_gb - free_gb, 2)
            used_pct = round((used_gb / total_gb) * 100, 2)
            return free_pct, used_pct, used_gb

        size_query = f"node_filesystem_size_bytes{{instance_id=\"{instance_id}\"}}"
        free_query = f"node_filesystem_free_bytes{{instance_id=\"{instance_id}\"}}"

        size_data = self.prometheus.custom_query(query=size_query)
        free_space_data = self.prometheus.custom_query(query=free_query)

        data = {}
        for size_metric in size_data:
            mountpoint = size_metric['metric']['mountpoint']

            for free_metric in free_space_data:
                if free_metric['metric']['mountpoint'] == mountpoint:
                    total_size_gb = bytes_to_gb(size_metric['value'][1])
                    free_space_gb = bytes_to_gb(free_metric['value'][1])

                    free_pct, used_pct, used_gb = calculate_percentages(free_space_gb, total_size_gb)

                    data[mountpoint] = {
                        'device': size_metric['metric']['device'],
                        'total_size': total_size_gb,
                        'free_space': free_space_gb,
                        'free_space_percentage': free_pct,
                        'used': used_gb,
                        'used_percentage': used_pct
                    }

        return data

    def get_disk_usage(self, instance_id: str, mountpoint: Optional[str] = None) -> dict:
        query = self._build_disk_usage_query(instance_id, mountpoint)
        usage_data = self.prometheus.custom_query(query=query)
        return self._parse_usage_data(usage_data)

    def get_disk_historical_usage(
        self,
        instance_id: str,
        start_time: datetime,
        end_time: datetime,
        step: int,
        mountpoint: Optional[str] = None
    ) -> dict:
        query = self._build_disk_usage_query(instance_id, mountpoint)
        historical_data = self.prometheus.custom_query_range(
            query=query,
            start_time=start_time,
            end_time=end_time,
            step=step
        )
        return self._parse_historical_data(historical_data)

    def _build_disk_usage_query(self, instance_id: str, mountpoint: str = None) -> str:
        mp = f', mountpoint="{mountpoint}"' if mountpoint else ""
        return (
            '100 - '
            f'node_filesystem_avail_bytes{{instance_id="{instance_id}"{mp}}} / '
            f'node_filesystem_size_bytes{{instance_id="{instance_id}"{mp}}} * 100'
        )

    def _parse_usage_data(self, usage_data) -> dict:
        current_usage = {}
        for item in usage_data:
            current_usage[item['metric']['mountpoint']] = round(float(item['value'][1]), 2)
        return current_usage

    def _parse_historical_data(self, historical_data) -> dict:
        historical_usage = {}
        for item in historical_data:
            historical_usage[item['metric']['mountpoint']] = [
                round(float(value[1]), 2) for value in item['values']
            ]
        return historical_usage
