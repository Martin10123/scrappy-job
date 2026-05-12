from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Dict, List, Optional, Tuple

from app.logger import logger
from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.services.job_normalizer import detect_english_requirement, detect_work_mode, format_skill, normalize_skills, skill_category

class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def list_jobs(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        contract_type: Optional[str] = None,
        work_mode: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Job], int]:
        logger.debug(
            "JobService: solicitando listado de jobs filtrado "
            f"source={source} city={city} contract_type={contract_type} work_mode={work_mode} search={search} "
            f"limit={limit} offset={offset}"
        )
        jobs = self.repository.get_filtered(
            source=source,
            city=city,
            contract_type=contract_type,
            work_mode=work_mode,
            search=search,
            limit=limit,
            offset=offset,
        )
        total = self.repository.count_filtered(
            source=source,
            city=city,
            contract_type=contract_type,
            work_mode=work_mode,
            search=search,
        )
        logger.info(f"JobService: {len(jobs)} jobs recuperados de {total} totales")
        return jobs, total

    def get_job(self, job_id: int) -> Optional[Job]:
        logger.debug(f"JobService: solicitando job id={job_id}")
        job = self.repository.get_by_id(job_id)
        if job:
            logger.info(f"JobService: job encontrado id={job_id} title={job.title}")
        else:
            logger.warning(f"JobService: job no encontrado id={job_id}")
        return job

    def get_analytics_overview(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        top_n: int = 10,
    ) -> Dict[str, object]:
        top_n = max(top_n, 10)
        jobs = self.repository.get_all_filtered_for_analytics(source=source, city=city)

        source_counter = Counter(job.source for job in jobs if job.source)
        city_counter = Counter(job.city for job in jobs if job.city)
        contract_counter = Counter(job.contract_type for job in jobs if job.contract_type)
        work_mode_counter = Counter(
            (job.work_mode or detect_work_mode(job.location_text or job.city, job.contract_type))
            for job in jobs
            if (job.work_mode or job.location_text or job.city or job.contract_type)
        )
        seniority_counter = Counter(job.seniority for job in jobs if job.seniority)

        technical_skill_counter = Counter()
        soft_skill_counter = Counter()
        english_requirement_counter = Counter()
        english_requirement_monthly = Counter()
        english_requirement_monthly_total = Counter()
        salary_mins = []
        salary_maxs = []
        monthly_counter = Counter()

        for job in jobs:
            if isinstance(job.skills, list):
                for skill in job.skills:
                    normalized = normalize_skills([skill])
                    if not normalized:
                        continue

                    display_skill = format_skill(normalized[0])
                    if skill_category(normalized[0]) == "soft":
                        soft_skill_counter[display_skill] += 1
                    else:
                        technical_skill_counter[display_skill] += 1

            if job.salary_min is not None:
                salary_mins.append(job.salary_min)
            if job.salary_max is not None:
                salary_maxs.append(job.salary_max)

            date_ref = job.published_at or job.scraped_at
            if date_ref:
                month_key = date_ref.strftime("%Y-%m")
                monthly_counter[month_key] += 1
                english_requirement_monthly_total[month_key] += 1

            english_required = getattr(job, "english_required", None)
            if english_required is None:
                english_required = detect_english_requirement(job.title, job.description, job.location_text)

            if english_required is True:
                english_requirement_counter["required"] += 1
                if date_ref:
                    english_requirement_monthly[date_ref.strftime("%Y-%m")] += 1
            elif english_required is False:
                english_requirement_counter["not_required"] += 1
            else:
                english_requirement_counter["unknown"] += 1

        english_requirement_monthly_trend = {}
        for month_key in sorted(english_requirement_monthly_total.keys()):
            required_count = english_requirement_monthly.get(month_key, 0)
            total_count = english_requirement_monthly_total[month_key]
            english_requirement_monthly_trend[month_key] = {
                "required": required_count,
                "total": total_count,
                "pct_required": round((required_count / total_count) * 100.0, 2) if total_count else 0.0,
            }

        return {
            "total_jobs": len(jobs),
            "top_sources": dict(source_counter.most_common(top_n)),
            "top_cities": dict(city_counter.most_common(top_n)),
            "contract_type_distribution": dict(contract_counter.most_common(top_n)),
            "work_mode_distribution": dict(work_mode_counter.most_common(top_n)),
            "seniority_distribution": dict(seniority_counter.most_common(top_n)),
            "technical_skills": dict(technical_skill_counter.most_common(top_n)),
            "soft_skills": dict(soft_skill_counter.most_common(top_n)),
            "top_skills": dict(technical_skill_counter.most_common(top_n)),
            "english_requirement_distribution": dict(english_requirement_counter),
            "english_requirement_monthly_trend": english_requirement_monthly_trend,
            "salary": {
                "avg_salary_min": round(mean(salary_mins), 2) if salary_mins else None,
                "avg_salary_max": round(mean(salary_maxs), 2) if salary_maxs else None,
                "with_salary_min_count": len(salary_mins),
                "with_salary_max_count": len(salary_maxs),
            },
            "monthly_trend": dict(sorted(monthly_counter.items())),
        }

    def get_demand_forecast(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        top_n: int = 10,
        months_ahead: int = 3,
    ) -> Dict[str, object]:
        top_n = max(top_n, 10)
        jobs = self.repository.get_all_filtered_for_analytics(source=source, city=city)

        technical_counter, soft_counter = self._build_skill_monthly_counters_by_category(jobs)
        technical_skills = self._build_skill_forecast_series(technical_counter, top_n, months_ahead)
        soft_skills = self._build_skill_forecast_series(soft_counter, top_n, months_ahead)

        return {
            "generated_at": datetime.utcnow(),
            "horizon_months": months_ahead,
            "top_n": top_n,
            "total_jobs_analyzed": len(jobs),
            "technical_skills": technical_skills,
            "soft_skills": soft_skills,
            "skills": technical_skills,
        }

    def get_forecast_confidence(
        self,
        source: Optional[str] = None,
        city: Optional[str] = None,
        top_n: int = 10,
        test_horizon_months: int = 2,
    ) -> Dict[str, object]:
        top_n = max(top_n, 10)
        jobs = self.repository.get_all_filtered_for_analytics(source=source, city=city)
        technical_counter, soft_counter = self._build_skill_monthly_counters_by_category(jobs)
        technical_skills = self._build_skill_confidence_series(technical_counter, top_n, test_horizon_months)
        soft_skills = self._build_skill_confidence_series(soft_counter, top_n, test_horizon_months)

        return {
            "generated_at": datetime.utcnow(),
            "top_n": top_n,
            "test_horizon_months": test_horizon_months,
            "total_jobs_analyzed": len(jobs),
            "technical_skills": technical_skills,
            "soft_skills": soft_skills,
            "skills": technical_skills,
        }

    @staticmethod
    def _normalize_skills(skills: object) -> List[str]:
        return normalize_skills(skills)

    @staticmethod
    def _build_skill_monthly_counter(jobs: List[Job]) -> Dict[str, Counter]:
        skill_monthly_counter: Dict[str, Counter] = {}

        for job in jobs:
            date_ref = job.published_at or job.scraped_at
            if not date_ref:
                continue

            month_key = date_ref.strftime("%Y-%m")
            skills = JobService._normalize_skills(job.skills)
            if not skills:
                continue

            for skill in skills:
                # Desnormalizar para mostrar de forma legible
                display_skill = denormalize_skill(skill)
                if display_skill not in skill_monthly_counter:
                    skill_monthly_counter[display_skill] = Counter()
                skill_monthly_counter[display_skill][month_key] += 1

        return skill_monthly_counter

    @staticmethod
    def _build_skill_monthly_counters_by_category(jobs: List[Job]) -> Tuple[Dict[str, Counter], Dict[str, Counter]]:
        technical_skill_monthly_counter: Dict[str, Counter] = {}
        soft_skill_monthly_counter: Dict[str, Counter] = {}

        for job in jobs:
            date_ref = job.published_at or job.scraped_at
            if not date_ref:
                continue

            month_key = date_ref.strftime("%Y-%m")
            skills = JobService._normalize_skills(job.skills)
            if not skills:
                continue

            for skill in skills:
                display_skill = format_skill(skill)
                if not display_skill:
                    continue

                target_counter = soft_skill_monthly_counter if skill_category(skill) == "soft" else technical_skill_monthly_counter
                if display_skill not in target_counter:
                    target_counter[display_skill] = Counter()
                target_counter[display_skill][month_key] += 1

        return technical_skill_monthly_counter, soft_skill_monthly_counter

    @staticmethod
    def _build_skill_forecast_series(
        skill_monthly_counter: Dict[str, Counter],
        top_n: int,
        months_ahead: int,
    ) -> List[Dict[str, object]]:
        ranked_skills = sorted(
            skill_monthly_counter.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        )[:top_n]

        results: List[Dict[str, object]] = []
        for skill, monthly_counts in ranked_skills:
            months = sorted(monthly_counts.keys())
            observed_values = [int(monthly_counts[month]) for month in months]

            predicted_values = JobService._forecast_linear(observed_values, months_ahead)
            next_months = JobService._next_months(months[-1], months_ahead)

            history = [{"month": month, "count": int(monthly_counts[month])} for month in months]
            forecast = [
                {"month": month, "count": int(round(max(value, 0.0)))}
                for month, value in zip(next_months, predicted_values)
            ]

            observed_total = sum(point["count"] for point in history)
            projected_total = sum(point["count"] for point in forecast)

            baseline = observed_values[-1] if observed_values else 0
            projected_last = forecast[-1]["count"] if forecast else 0
            growth_pct = None
            if baseline > 0:
                growth_pct = round(((projected_last - baseline) / baseline) * 100.0, 2)

            results.append(
                {
                    "skill": skill,
                    "history": history,
                    "forecast": forecast,
                    "total_observed": observed_total,
                    "projected_total": projected_total,
                    "growth_pct": growth_pct,
                }
            )

        return results

    @staticmethod
    def _build_skill_confidence_series(
        skill_monthly_counter: Dict[str, Counter],
        top_n: int,
        test_horizon_months: int,
    ) -> List[Dict[str, object]]:
        ranked_skills = sorted(
            skill_monthly_counter.items(),
            key=lambda item: sum(item[1].values()),
            reverse=True,
        )[:top_n]

        results: List[Dict[str, object]] = []
        for skill, monthly_counts in ranked_skills:
            months = sorted(monthly_counts.keys())
            values = [int(monthly_counts[month]) for month in months]

            max_test = min(test_horizon_months, max(len(values) - 1, 0))
            if max_test <= 0:
                continue

            train_values = values[:-max_test]
            test_values = values[-max_test:]

            predictions = JobService._forecast_linear(train_values, max_test)
            rounded_predictions = [int(round(max(pred, 0.0))) for pred in predictions]

            abs_errors = [abs(real - pred) for real, pred in zip(test_values, rounded_predictions)]
            mae = mean(abs_errors) if abs_errors else 0.0

            pct_errors = [
                (abs(real - pred) / real) * 100.0
                for real, pred in zip(test_values, rounded_predictions)
                if real > 0
            ]
            mape = round(mean(pct_errors), 2) if pct_errors else None

            results.append(
                {
                    "skill": skill,
                    "train_points": len(train_values),
                    "test_points": len(test_values),
                    "mae": round(float(mae), 2),
                    "mape_pct": mape,
                    "confidence_level": JobService._confidence_label(mape),
                }
            )

        return results

    @staticmethod
    def _forecast_linear(values: List[int], months_ahead: int) -> List[float]:
        if months_ahead <= 0:
            return []
        if not values:
            return [0.0] * months_ahead
        if len(values) == 1:
            return [float(values[0])] * months_ahead

        x_values = list(range(len(values)))
        x_mean = mean(x_values)
        y_mean = mean(values)

        denominator = sum((x - x_mean) ** 2 for x in x_values)
        if denominator == 0:
            return [float(values[-1])] * months_ahead

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        slope = numerator / denominator
        intercept = y_mean - (slope * x_mean)

        return [max(0.0, intercept + slope * x) for x in range(len(values), len(values) + months_ahead)]

    @staticmethod
    def _next_months(last_month: str, months_ahead: int) -> List[str]:
        year, month = [int(part) for part in last_month.split("-")]
        result = []

        current_year = year
        current_month = month
        for _ in range(months_ahead):
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
            result.append(f"{current_year:04d}-{current_month:02d}")

        return result

    @staticmethod
    def _confidence_label(mape: Optional[float]) -> str:
        if mape is None:
            return "insufficient-data"
        if mape <= 10:
            return "high"
        if mape <= 20:
            return "medium"
        return "low"
