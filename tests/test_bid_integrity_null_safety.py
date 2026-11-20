import importlib
import inspect
import unittest


TARGET_MODULES = (
    "proposal_evaluation",
    "bid_pricing_ingestion",
    "statutory_compliance",
    "ownership_conflict",
)

MALFORMED_PAYLOADS = (
    None,
    {},
    [],
    "",
    0,
    {"kyb_data": None, "statutory_records": None, "competing_bids": None},
)


def _dummy_arg_for_param(param: inspect.Parameter):
    if param.default is not inspect.Parameter.empty:
        return param.default
    name = param.name.lower()
    if "list" in name or "records" in name or "bids" in name or "items" in name or "rows" in name:
        return []
    if "dict" in name or "data" in name or "payload" in name or "kyb" in name or "profile" in name:
        return {}
    if "str" in name or "text" in name or "id" in name or "code" in name or "name" in name:
        return ""
    return None


class BidIntegrityNullSafetyTests(unittest.TestCase):
    def test_modules_import_cleanly(self):
        for mod_name in TARGET_MODULES:
            with self.subTest(module=mod_name):
                module = importlib.import_module(mod_name)
                self.assertIsNotNone(module)

    def test_evaluate_bid_integrity_package_handles_none_and_empty_inputs(self):
        module = importlib.import_module("proposal_evaluation")
        self.assertTrue(
            hasattr(module, "evaluate_bid_integrity_package"),
            "evaluate_bid_integrity_package must remain exported from proposal_evaluation",
        )
        fn = getattr(module, "evaluate_bid_integrity_package")

        for payload in MALFORMED_PAYLOADS:
            with self.subTest(payload=payload):
                if isinstance(payload, dict):
                    result = fn(
                        kyb_data=payload.get("kyb_data"),
                        statutory_records=payload.get("statutory_records"),
                        competing_bids=payload.get("competing_bids"),
                    )
                else:
                    result = fn(kyb_data=payload)
                self.assertIsInstance(result, dict)
                self.assertIn("package_status", result)
                self.assertIsInstance(result["package_status"], str)
                self.assertTrue(result["package_status"].strip())

    def test_module_public_callables_tolerate_null_and_empty_arguments(self):
        for mod_name in TARGET_MODULES:
            module = importlib.import_module(mod_name)
            public_callables = [
                getattr(module, attr)
                for attr in dir(module)
                if not attr.startswith("_") and callable(getattr(module, attr))
            ]
            for fn in public_callables:
                if getattr(fn, "__module__", None) != mod_name:
                    continue
                sig = inspect.signature(fn)
                required_positional = [
                    p
                    for p in sig.parameters.values()
                    if p.kind
                    in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                    and p.default is inspect.Parameter.empty
                ]
                with self.subTest(module=mod_name, callable=fn.__name__):
                    try:
                        if not required_positional:
                            outcome = fn()
                        else:
                            args = [_dummy_arg_for_param(p) for p in required_positional]
                            outcome = fn(*args)
                    except (TypeError, ValueError):
                        continue
                    self.assertIsNotNone(outcome)


if __name__ == "__main__":
    unittest.main()