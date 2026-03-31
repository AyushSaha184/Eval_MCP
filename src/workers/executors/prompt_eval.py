from __future__ import annotations

from collections import defaultdict

from core.metrics_registry import get_metric_definition
from db.repositories.metrics import MetricsRepository
from db.repositories.runs import RunsRepository
from domain.enums import ArtifactType, CaseResultStatus, MetricDirection
from domain.schemas import DatasetReference
from eval_backends.deepeval_runner import DeepEvalRunner
from eval_backends.llm_runner import LLMRunner
from eval_backends.ragas_runner import RagasRunner
from services.artifacts import ArtifactService
from services.datasets import DatasetService


class PromptEvalExecutor:
    def __init__(self, session) -> None:
        self.session = session
        self.metrics_repo = MetricsRepository(session)
        self.runs_repo = RunsRepository(session)
        self.datasets = DatasetService(session)
        self.artifacts = ArtifactService(session)
        self.llm_runner = LLMRunner()
        self.deepeval = DeepEvalRunner()
        self.ragas = RagasRunner()

    async def execute(self, run) -> None:
        snapshot = await self.runs_repo.get_snapshot(run.id)
        dataset_reference = snapshot.dataset_snapshot_json
        dataset, cases = await self.datasets.resolve_dataset(
            run.project_id,
            DatasetReference(
                dataset_id=dataset_reference.get("dataset_id"),
                dataset_name=dataset_reference.get("dataset_name"),
                version_hash=dataset_reference.get("version_hash"),
            ),
        )
        selected_indices = set(dataset_reference.get("selected_case_indices", []))
        if selected_indices:
            cases = [case for case in cases if case.case_index in selected_indices]

        transcripts: list[dict] = []
        metric_buckets: dict[str, list[float]] = defaultdict(list)
        passing_cases = 0
        total_cases = len(cases)
        await self.runs_repo.update_progress(run_db_id=run.id, processed_cases=0, total_cases=total_cases)

        for index, case in enumerate(cases, start=1):
            generation = await self.llm_runner.generate(
                prompt_snapshot=snapshot.prompt_snapshot_json,
                input_text=case.input_text,
                expected_output=case.expected_output,
                model_config=snapshot.model_config_snapshot_json,
                runtime_config=snapshot.runtime_config_snapshot_json,
            )
            metric_results = await self.deepeval.score_case(
                metrics=run.metrics_requested_json,
                actual_output=generation.output_text,
                expected_output=case.expected_output,
                context=case.context_json,
            )
            if any(get_metric_definition(metric).provider == "ragas" for metric in run.metrics_requested_json):
                metric_results.extend(
                    await self.ragas.score_case(
                        metrics=run.metrics_requested_json,
                        question=case.input_text,
                        actual_output=generation.output_text,
                        expected_output=case.expected_output,
                        retrieved_context=generation.retrieved_context,
                        expected_context=case.context_json,
                    )
                )

            case_passed = all(result.passed is not False for result in metric_results)
            case_result = await self.metrics_repo.create_case_result(
                run_id=run.id,
                dataset_case_id=case.id,
                case_index=case.case_index,
                input_text_snapshot=case.input_text,
                actual_output=generation.output_text,
                expected_output_snapshot=case.expected_output,
                retrieved_context_snapshot_json=generation.retrieved_context,
                latency_ms=generation.latency_ms,
                token_usage_json=generation.token_usage,
                status=CaseResultStatus.PASSED if case_passed else CaseResultStatus.FAILED,
                failure_reason=None if case_passed else "metric_threshold_failed",
                metadata_json=generation.metadata,
            )
            await self.metrics_repo.create_metric_results(
                [
                    {
                        "run_id": run.id,
                        "case_result_id": case_result.id,
                        "metric_name": result.metric_name,
                        "metric_family": result.metric_family,
                        "score": result.score,
                        "threshold": result.threshold,
                        "direction": result.direction,
                        "passed": result.passed,
                        "details_json": result.details,
                    }
                    for result in metric_results
                ]
            )
            for result in metric_results:
                metric_buckets[result.metric_name].append(result.score)
            if case_passed:
                passing_cases += 1
            transcripts.append(
                {
                    "case_index": case.case_index,
                    "input_text": case.input_text,
                    "expected_output": case.expected_output,
                    "actual_output": generation.output_text,
                }
            )
            await self.runs_repo.update_progress(run_db_id=run.id, processed_cases=index)

        aggregate_rows = []
        for metric_name, values in metric_buckets.items():
            definition = get_metric_definition(metric_name)
            score = sum(values) / max(len(values), 1)
            if definition.direction == MetricDirection.HIGHER_IS_BETTER:
                passed = score >= (definition.default_threshold or 0.0)
            else:
                passed = score <= (definition.default_threshold or 0.0)
            aggregate_rows.append(
                {
                    "run_id": run.id,
                    "case_result_id": None,
                    "metric_name": metric_name,
                    "metric_family": definition.family,
                    "score": round(score, 6),
                    "threshold": definition.default_threshold,
                    "direction": definition.direction,
                    "passed": passed,
                    "details_json": {"provider": definition.provider, "samples": len(values)},
                }
            )
        if aggregate_rows:
            await self.metrics_repo.create_metric_results(aggregate_rows)
        pass_rate = passing_cases / max(total_cases, 1) if total_cases else 0.0
        if snapshot.runtime_config_snapshot_json.get("include_artifacts"):
            await self.artifacts.persist_json(
                run_db_id=run.id,
                run_public_id=run.run_id,
                artifact_type=ArtifactType.TRANSCRIPT,
                filename="transcripts.json",
                payload=transcripts,
                metadata={"cases": len(transcripts)},
            )
        await self.runs_repo.finalize_success(
            run_db_id=run.id,
            pass_rate=round(pass_rate, 6),
            processed_cases=total_cases,
            total_cases=total_cases,
        )
