import base64
import json
import os
import urllib.error
import urllib.request


GEMMA_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)


class GemmaReportError(RuntimeError):
    pass


class GemmaReportService:
    def __init__(self, api_key=None, model=None, timeout=30):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMMA_MODEL", "gemma-4-26b-a4b-it")
        self.timeout = timeout

    @property
    def configured(self):
        return bool(self.api_key)

    def generate(self, context, image_bytes=None, image_mime_type="image/png"):
        if not self.api_key:
            raise GemmaReportError("GEMINI_API_KEY is not configured.")

        prompt = (
            "Create a cautious surveillance incident report from the supplied image and "
            "run metadata. Treat the anomaly category as a hypothesis, not a confirmed fact. "
            "Do not infer identities, intent, injuries, fault, protected traits, or events not "
            "visually supported. Use concise, concrete observations. Return only valid JSON "
            "with these keys: incident_summary (string), timestamp (string), "
            "visual_observations (array of 3 strings), supporting_evidence (array of 1-3 "
            "strings), evidence_note (string), recommended_next_steps (array of 3 strings), "
            "limitations (string). Each recommendation must preserve human review and lawful "
            "authorization. Metadata:\n" + json.dumps(context, separators=(",", ":"))
        )
        parts = [{"text": prompt}]
        if image_bytes:
            parts.insert(
                0,
                {
                    "inline_data": {
                        "mime_type": image_mime_type,
                        "data": base64.b64encode(image_bytes).decode("ascii"),
                    }
                },
            )
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        request = urllib.request.Request(
            GEMMA_API_URL.format(model=self.model),
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read(500).decode("utf-8", errors="replace")
            raise GemmaReportError(f"Gemma API returned HTTP {error.code}: {detail}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise GemmaReportError(f"Gemma API request failed: {error}") from error

        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            report = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise GemmaReportError("Gemma returned an invalid structured report.") from error
        self._validate(report)
        return report

    @staticmethod
    def _validate(report):
        string_fields = {
            "incident_summary", "timestamp", "evidence_note", "limitations"
        }
        list_fields = {
            "visual_observations", "supporting_evidence", "recommended_next_steps"
        }
        if not isinstance(report, dict):
            raise GemmaReportError("Gemma report must be a JSON object.")
        if any(not isinstance(report.get(key), str) or not report[key].strip() for key in string_fields):
            raise GemmaReportError("Gemma report contains an invalid text field.")
        for key in list_fields:
            values = report.get(key)
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise GemmaReportError(f"Gemma report contains an invalid {key} field.")

