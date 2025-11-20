# app/agents/data_agent.py

import json
import re
import logging
from typing import Any, List, Tuple, Optional

from app.llm_client import chat_completion, ALL_PROVIDERS
from app.agents.tools import (
    load_csv_tool,
    correlation_tool,
    summary_stats_tool,
    top_group_by_tool,
    filter_tool
)

logger = logging.getLogger(__name__)


# ============================================================
# Utility Functions
# ============================================================

def extract_json(text: str) -> str:
    """Strip fenced code blocks and return raw JSON text."""
    if not text:
        return text
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def safe_json_load(s: str):
    """Safe JSON loader returning (obj, error)."""
    try:
        return json.loads(s), None
    except Exception as e:
        return None, str(e)


def serialize_result(res: Any, max_rows: int = 3):
    """Make tool outputs JSON-friendly for LLM repair context."""
    try:
        if hasattr(res, "columns") and hasattr(res, "head"):
            preview_df = res.head(max_rows)
            preview = (
                preview_df.to_dict(orient="records")
                if hasattr(preview_df, "to_dict")
                else []
            )
            return {
                "type": "dataframe",
                "columns": list(res.columns),
                "nrows": len(res),
                "preview": preview,
            }
        if hasattr(res, "head") and hasattr(res, "to_list"):
            return {
                "type": "series",
                "values": res.head(max_rows * 2).to_list()
            }
    except Exception:
        pass

    try:
        json.dumps(res)
        return res
    except Exception:
        return str(res)


def build_dataset_profile(df, max_rows: int = 3):
    """
    Produce a lightweight summary of the dataframe so the LLM can reason about
    the schema without us hard-coding column names.
    """
    if df is None or not hasattr(df, "head"):
        return {"columns": [], "preview": [], "row_count": 0}

    try:
        preview_df = df.head(max_rows)
        preview = (
            preview_df.to_dict(orient="records")
            if hasattr(preview_df, "to_dict")
            else []
        )
        return {
            "columns": list(df.columns),
            "row_count": int(len(df)),
            "preview": preview,
        }
    except Exception:
        return {"columns": [], "preview": [], "row_count": 0}


def truncate_text(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def format_tool_outputs_for_prompt(tool_outputs: List[dict]) -> str:
    try:
        raw = json.dumps(tool_outputs, ensure_ascii=False, default=str)
    except Exception:
        raw = str(tool_outputs)
    return truncate_text(raw, 2500)


# ============================================================
# Tool Registry
# ============================================================

VALID_TOOLS = {
    "load_csv": load_csv_tool,
    "correlation": correlation_tool,
    "summary_stats": summary_stats_tool,
    "top_group_by": top_group_by_tool,
    "filter": filter_tool,
}

REQUIRED_ARGS = {
    "load_csv": [],
    "correlation": ["column_x", "column_y"],
    "summary_stats": [],
    "top_group_by": ["group_by", "value_col"],
    "filter": ["column", "op", "value"],
}

COLUMN_ARG_NAMES = {
    "correlation": ["column_x", "column_y", "group_by"],
    "summary_stats": ["column", "group_by"],
    "top_group_by": ["group_by", "value_col"],
    "filter": ["column"],
}


# ============================================================
# PROMPTS (FULLY ESCAPED)
# ============================================================

BASE_PROMPT = (
    "SYSTEM: You are an analytical, tool-using data scientist. "
    "You MUST output ONLY a JSON LIST. The LAST element MUST be a final "
    "answer as {{\"final_answer\": \"<value>\"}}.\n\n"
    "DATASET SNAPSHOT:\n"
    "{data_profile}\n\n"
    "Detected columns (use EXACT spellings or inspect dataframe head): "
    "{allowed_columns}\n\n"
    "TOOL SCHEMA:\n"
    "  {{\"action\": \"load_csv\", \"args\": {{\"path\": \"<csv_url>\"}}}},\n"
    "  {{\"action\": \"correlation\", \"args\": {{\"column_x\": \"<col>\", "
    "\"column_y\": \"<col>\", \"group_by\": \"<optional>\"}}}},\n"
    "  {{\"action\": \"summary_stats\", \"args\": {{\"column\": "
    "\"<optional>\", \"group_by\": \"<optional>\"}}}},\n"
    "  {{\"action\": \"top_group_by\", \"args\": {{\"group_by\": \"<col>\", "
    "\"value_col\": \"<col>\", \"n\": <int>}}}},\n"
    "  {{\"action\": \"filter\", \"args\": {{\"column\": \"<col>\", \"op\": "
    "\"<op>\", \"value\": <val>}}}},\n\n"
    "RULES:\n"
    "- Carefully read the question and plan each tool call before "
    "answering.\n"
    "- ALWAYS inspect the loaded dataframe before running aggregations.\n"
    "- Cross-check calculations (e.g., recompute statistics or validate "
    "units) when possible.\n"
    "- NEVER invent column names or statistics; reference only actual "
    "dataframe columns.\n"
    "- NEVER output plain text; ALWAYS output JSON per schema and end with "
    "final_answer.\n\n"
    "EXAMPLE STRUCTURE:\n"
    "[\n"
    "  {{\"action\": \"load_csv\", \"args\": {{\"path\": \"<csv_url>\"}}}},\n"
    "  {{\"action\": \"summary_stats\", \"args\": {{\"column\": "
    "\"<column_name>\"}}}},\n"
    "  {{\"final_answer\": \"<result>\"}}\n"
    "]\n\n"
    "USER: {user_payload}\n"
)


REPAIR_INVALID_JSON_PROMPT = (
    "The previous output contained INVALID JSON. Here is the output:\n"
    "{bad_output}\n\n"
    "Fix it to valid JSON list ONLY. Follow TOOL SCHEMA and MUST include "
    "{{\"final_answer\": \"<value>\"}} as last element.\n"
    "Allowed columns: {allowed_columns}\n"
    "Return ONLY corrected JSON."
)

REPAIR_INVALID_COLUMNS_PROMPT = (
    "Your previous plan referenced invalid columns.\n"
    "Invalid references: {invalid_columns}\n"
    "Allowed columns: {allowed_columns}\n"
    "Return ONLY corrected JSON list per schema with valid columns."
)

REPAIR_ADD_FINAL_PROMPT = (
    "The previous tool plan executed but DID NOT include a "
    "final_answer.\n"
    "Executed tool outputs:\n"
    "{tool_outputs}\n\n"
    "Append a final step {{\"final_answer\": \"<value>\"}}.\n"
    "Return ONLY the corrected JSON list.\n"
    "Allowed columns: {allowed_columns}"
)

VERIFIER_SYSTEM_PROMPT = (
    "You verify analytical answers using structured data. Respond ONLY with "
    "JSON."
)

VERIFICATION_PROMPT = (
    "Question:\n{question}\n\n"
    "Proposed final answer: {final_answer}\n\n"
    "Tool outputs (JSON):\n{tool_outputs}\n\n"
    "Return JSON with keys final_answer, confidence (high|medium|low), "
    "reason."
)


# ============================================================
# DataAgent Class
# ============================================================

class DataAgent:
    def __init__(self):
        pass

    @staticmethod
    def _model_attempts(passes: int = 1) -> List[Tuple[int, int]]:
        """
        Return ordered list of (provider_idx, model_idx) pairs covering the
        configured providers. Multiple passes let us retry the roster again if
        every model fails the first time.
        """
        attempts: List[Tuple[int, int]] = []

        if not ALL_PROVIDERS:
            return attempts

        for _ in range(max(1, passes)):
            for p_idx, provider in enumerate(ALL_PROVIDERS):
                models = provider.get("models") or [provider.get("model")]
                models = [m for m in models if m]
                if not models:
                    continue
                for m_idx in range(len(models)):
                    attempts.append((p_idx, m_idx))

        return attempts

    @staticmethod
    def _normalize_and_validate_plan_columns(
        plan, allowed_columns: List[str]
    ):
        allowed_map = {c.lower(): c for c in allowed_columns}
        invalid = []

        for st in plan:
            action = st.get("action")
            if action not in COLUMN_ARG_NAMES:
                continue

            args = st.get("args", {}) or {}
            for arg_name in COLUMN_ARG_NAMES[action]:
                val = args.get(arg_name)
                if not isinstance(val, str):
                    continue
                normalized = allowed_map.get(val.lower())
                if normalized:
                    args[arg_name] = normalized
                else:
                    invalid.append(
                        {
                            "action": action,
                            "arg": arg_name,
                            "value": val,
                        }
                    )
        return invalid, plan

    async def run(
        self,
        question: str,
        df=None,
        csv_url=None,
        attempt_number: int = 1,
        prior_feedback: Optional[str] = None,
    ):
        if not csv_url:
            return {"error": "csv_url missing"}

        cached_df = df
        if cached_df is None:
            try:
                cached_df = await load_csv_tool({"path": csv_url}, None)
            except Exception as exc:
                logger.error(
                    f"[DataAgent] Failed to load CSV {csv_url}: {exc}"
                )
                return {"error": "csv_load_failed", "details": str(exc)}

        dataset_profile = build_dataset_profile(cached_df)
        allowed_columns = dataset_profile.get("columns", [])
        allowed_columns_text = (
            ", ".join(allowed_columns) if allowed_columns else "Not detected"
        )
        data_profile_str = json.dumps(
            dataset_profile, ensure_ascii=False, default=str
        )

        context_lines = [
            "Return ONLY tool JSON per schema.",
            f"This is attempt #{attempt_number}. You must maximize "
            "accuracy.",
            "Double-check calculations before producing final_answer.",
        ]
        if prior_feedback:
            context_lines.append(f"Server feedback: {prior_feedback}")

        user_payload = json.dumps(
            {
                "question": question,
                "csv_url": csv_url,
                "context": " ".join(context_lines),
            },
            ensure_ascii=False,
        )

        base_prompt = BASE_PROMPT.format(
            user_payload=user_payload,
            allowed_columns=allowed_columns_text,
            data_profile=data_profile_str,
        )

        model_attempts = self._model_attempts()
        if not model_attempts:
            return {"error": "No LLM providers configured."}

        def resolve_csv_target(arg_dict):
            for key in (
                "path",
                "file_path",
                "url",
                "dataset",
                "file",
                "csv_path",
            ):
                val = arg_dict.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            return None

        # Outer loop: walk across providers/models
        for attempt_idx, (p_idx, m_idx) in enumerate(model_attempts):
            # === 1. ASK MODEL FOR INITIAL PLAN ===
            try:
                llm_resp = await chat_completion(
                    [{"role": "system", "content": base_prompt}],
                    provider_index=p_idx,
                    model_index=m_idx,
                )
            except Exception as e:
                logger.warning(
                    f"[DataAgent] LLM failed @ attempt {attempt_idx} "
                    f"(provider={p_idx}, model={m_idx}): {e}"
                )
                continue

            clean_text = extract_json(llm_resp)
            plan, err = safe_json_load(clean_text)

            # === 2. JSON INVALID → TRY REPAIR LOOP (same model) ===
            if err:
                logger.warning(f"[DataAgent] Bad JSON: {err}")

                repaired = None
                for r_try in range(3):
                    repair_prompt = REPAIR_INVALID_JSON_PROMPT.format(
                        bad_output=clean_text,
                        allowed_columns=allowed_columns_text,
                    )
                    try:
                        rep = await chat_completion(
                            [
                                {"role": "system", "content": base_prompt},
                                {"role": "user", "content": repair_prompt},
                            ],
                            provider_index=p_idx,
                            model_index=m_idx,
                        )
                    except Exception:
                        continue

                    rep_clean = extract_json(rep)
                    plan2, err2 = safe_json_load(rep_clean)
                    if plan2 and not err2:
                        repaired = plan2
                        break

                if repaired is None:
                    # failed repair → move to next model
                    continue
                plan = repaired

            # === Normalize plan to list ===
            if isinstance(plan, dict):
                plan = [plan]

            # Quick validation
            validated = True
            for st in plan:
                if "final_answer" in st:
                    continue
                if "action" not in st or st["action"] not in VALID_TOOLS:
                    validated = False
                    break

            if not validated:
                # ask to repair plan shape
                repair_prompt = REPAIR_INVALID_JSON_PROMPT.format(
                    bad_output=json.dumps(plan),
                    allowed_columns=allowed_columns_text,
                )
                try:
                    rep = await chat_completion(
                        [
                            {"role": "system", "content": base_prompt},
                            {"role": "user", "content": repair_prompt},
                        ],
                        provider_index=p_idx,
                        model_index=m_idx,
                    )
                    rep_clean = extract_json(rep)
                    plan2, err2 = safe_json_load(rep_clean)
                    if not plan2 or err2:
                        continue
                    plan = plan2
                except Exception:
                    continue

            # Column validation / normalization
            if allowed_columns:
                (
                    invalid_columns,
                    plan,
                ) = self._normalize_and_validate_plan_columns(
                    plan, allowed_columns
                )
            else:
                invalid_columns = []

            if invalid_columns:
                invalid_json = json.dumps(
                    invalid_columns, ensure_ascii=False
                )
                repair_prompt = REPAIR_INVALID_COLUMNS_PROMPT.format(
                    invalid_columns=invalid_json,
                    allowed_columns=allowed_columns_text,
                )
                try:
                    rep = await chat_completion(
                        [
                            {"role": "system", "content": base_prompt},
                            {"role": "user", "content": repair_prompt},
                        ],
                        provider_index=p_idx,
                        model_index=m_idx,
                    )
                except Exception:
                    continue

                rep_clean = extract_json(rep)
                plan2, err2 = safe_json_load(rep_clean)
                if not plan2 or err2:
                    continue
                if isinstance(plan2, dict):
                    plan2 = [plan2]
                plan = plan2

                if allowed_columns:
                    (
                        invalid_columns,
                        plan,
                    ) = self._normalize_and_validate_plan_columns(
                        plan, allowed_columns
                    )
                    if invalid_columns:
                        logger.warning(
                            "[DataAgent] Plan still has invalid "
                            f"columns: {invalid_columns}"
                        )
                        continue

            # === 3. EXECUTE PLAN ===
            tool_outputs = []
            tool_failed = False
            current_df = cached_df

            for st in plan:
                # Already final?
                if "final_answer" in st:
                    return st["final_answer"]

                action = st.get("action")
                args = dict(st.get("args", {}) or {})

                if action not in VALID_TOOLS:
                    tool_failed = True
                    break

                # required args check
                missing = [r for r in REQUIRED_ARGS[action] if r not in args]
                if missing:
                    tool_failed = True
                    break

                # run tool
                try:
                    if action == "load_csv":
                        target_path = resolve_csv_target(args) or csv_url
                        if (
                            isinstance(target_path, str)
                            and "<csv_url>" in target_path.lower()
                        ):
                            target_path = csv_url
                        if target_path == csv_url and cached_df is not None:
                            result = cached_df
                        else:
                            result = await load_csv_tool(
                                {"path": target_path}, current_df
                            )
                        current_df = result
                        args = {"path": target_path}
                    else:
                        result = await VALID_TOOLS[action](args, current_df)
                        if hasattr(result, "columns") and hasattr(
                            result, "head"
                        ):
                            current_df = result

                    last_result = result
                    tool_outputs.append(
                        {
                            "action": action,
                            "args": args,
                            "result": serialize_result(result),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"[DataAgent] Tool '{action}' failed: {e}"
                    )
                    tool_failed = True
                    break

            # Tool crash → try next model
            if tool_failed:
                continue

            # === 4. NO FINAL ANSWER → ASK MODEL TO APPEND ONE ===
            tool_outputs_json = format_tool_outputs_for_prompt(tool_outputs)
            final_repair_prompt = REPAIR_ADD_FINAL_PROMPT.format(
                tool_outputs=tool_outputs_json,
                allowed_columns=allowed_columns_text,
            )

            repaired_final = None
            for f_try in range(3):
                try:
                    rep = await chat_completion(
                        [
                            {"role": "system", "content": base_prompt},
                            {"role": "user", "content": final_repair_prompt},
                        ],
                        provider_index=p_idx,
                        model_index=m_idx,
                    )
                except Exception:
                    continue

                rep_clean = extract_json(rep)
                plan2, err2 = safe_json_load(rep_clean)
                if err2 or not plan2:
                    continue

                if isinstance(plan2, dict):
                    plan2 = [plan2]

                for s2 in plan2:
                    if "final_answer" in s2:
                        repaired_final = s2["final_answer"]
                        break

                if repaired_final:
                    verified_answer = await self._verify_final_answer(
                        question=question,
                        proposed_answer=repaired_final,
                        tool_outputs=tool_outputs,
                        provider_idx=p_idx,
                        model_idx=m_idx,
                    )
                    return verified_answer

            # failed to add final_answer with this model
            continue

        # exhausted all providers/models
        return {"error": "All LLM models failed to produce final_answer."}

    async def _verify_final_answer(
        self,
        question: str,
        proposed_answer: str,
        tool_outputs: List[dict],
        provider_idx: int,
        model_idx: int,
    ) -> str:
        """
        Ask the LLM to double-check its own answer using the collected tool
        outputs.
        """
        tool_outputs_text = format_tool_outputs_for_prompt(tool_outputs)
        verify_prompt = VERIFICATION_PROMPT.format(
            question=question,
            final_answer=proposed_answer,
            tool_outputs=tool_outputs_text,
        )

        try:
            resp = await chat_completion(
                [
                    {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": verify_prompt},
                ],
                provider_index=provider_idx,
                model_index=model_idx,
            )
        except Exception:
            return proposed_answer

        resp_clean = extract_json(resp)
        data, err = safe_json_load(resp_clean)
        if err or not isinstance(data, dict):
            return proposed_answer

        verified_answer = data.get("final_answer") or data.get("answer")
        if not verified_answer:
            return proposed_answer

        return verified_answer
