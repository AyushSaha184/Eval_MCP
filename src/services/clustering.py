from __future__ import annotations

from collections import defaultdict

from domain.schemas import FailureCluster


class ClusteringService:
    def cluster_failed_cases(self, case_bundles: list[dict], *, limit: int = 5) -> list[FailureCluster]:
        grouped: dict[str, dict] = defaultdict(lambda: {"case_ids": [], "inputs": [], "metric_name": None})
        for bundle in case_bundles:
            metrics = bundle.get("metrics", [])
            failed_metric = next((metric.metric_name for metric in metrics if metric.passed is False), None)
            failure_reason = bundle["case_result"].failure_reason or "execution_failure"
            cluster_key = failed_metric or failure_reason
            title = f"Failures in {cluster_key}" if failed_metric else failure_reason.replace("_", " ")
            grouped[cluster_key]["case_ids"].append(bundle["case_result"].id)
            grouped[cluster_key]["inputs"].append(bundle["case_result"].input_text_snapshot)
            grouped[cluster_key]["metric_name"] = failed_metric
            grouped[cluster_key]["title"] = title

        clusters = [
            FailureCluster(
                cluster_key=cluster_key,
                title=data["title"],
                metric_name=data["metric_name"],
                case_result_ids=data["case_ids"],
                size=len(data["case_ids"]),
                sample_inputs=data["inputs"][:3],
            )
            for cluster_key, data in grouped.items()
        ]
        clusters.sort(key=lambda item: (-item.size, item.cluster_key))
        return clusters[:limit]

