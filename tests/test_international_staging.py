from src.i18n_staging import get_text, is_rtl_language, normalize_language_code
from src.international_staging import format_country_currency, get_country_profile, normalize_country_code
from src.procurement_staging import get_procurement_config, summarize_thresholds


def test_default_country_and_fallback():
    assert normalize_country_code(None) == "NG"
    assert normalize_country_code("UNKNOWN") == "NG"
    profile = get_country_profile("NG")
    assert profile.currency_code == "NGN"
    assert profile.default_language == "en"


def test_currency_formatting_across_jurisdictions():
    assert "NGN" in format_country_currency(1500000, "NG")
    assert "EUR" in format_country_currency(25000, "FR")
    assert "GBP" in format_country_currency(12000, "GB")


def test_i18n_fallback_and_rtl():
    assert normalize_language_code("fr-FR") == "fr"
    assert normalize_language_code("zz") == "en"
    assert get_text("jurisdiction_label", "fr") == "Juridiction"
    assert get_text("jurisdiction_label", "zz") == "Jurisdiction"
    assert is_rtl_language("ar") is True
    assert is_rtl_language("en") is False


def test_procurement_staging_thresholds():
    cfg = get_procurement_config("NG")
    assert cfg.regime_code == "NG_PPA_BPP_STAGE_GATE"
    assert len(cfg.stages) == 4
    thresholds = summarize_thresholds("NG")
    assert "NGN" in thresholds["direct_limit"]
    assert "NGN" in thresholds["competitive_limit"]


def test_persistence_locale_defaults_and_migration(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import contextmanager
    import persistence

    db_file = tmp_path / "intl_persist_test.db"

    @contextmanager
    def _test_conn():
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(persistence, "get_connection", _test_conn)

    with _test_conn() as conn:
        conn.execute("CREATE TABLE link_click_analytics (id INTEGER PRIMARY KEY AUTOINCREMENT, link_type TEXT NOT NULL, client_slug TEXT DEFAULT 'global')")
        conn.execute("CREATE TABLE client_working_state (session_key TEXT PRIMARY KEY, scope_id TEXT NOT NULL DEFAULT 'global', state_json TEXT NOT NULL)")
        conn.execute(
            "INSERT INTO client_working_state (session_key, scope_id, state_json) VALUES (?, ?, ?)",
            ("legacy_sess", "org1", '{"k": 1}'),
        )

    persistence.log_link_click("vendor_portal", "demo_tenant")
    assert persistence.save_working_state("fr_sess", {"step": 2}, "org2", country_code="FR", currency_code="EUR", language_code="fr")

    with _test_conn() as conn:
        legacy_row = conn.execute("SELECT country_code, currency_code, language_code FROM client_working_state WHERE session_key = ?", ("legacy_sess",)).fetchone()
        assert tuple(legacy_row) == ("NG", "NGN", "en")

        fr_row = conn.execute("SELECT country_code, currency_code, language_code FROM client_working_state WHERE session_key = ?", ("fr_sess",)).fetchone()
        assert tuple(fr_row) == ("FR", "EUR", "fr")

        click_row = conn.execute("SELECT country_code, currency_code, language_code FROM link_click_analytics LIMIT 1").fetchone()
        assert tuple(click_row) == ("NG", "NGN", "en")

def test_country_jurisdiction_entity_tiers_and_domain_defaults():
    fr = get_country_profile("FR")
    assert fr.default_language == "fr"
    assert len(fr.entity_categories) >= 5
    assert any("Minist" in item or "tablissement" in item or "Collectivit" in item for item in fr.entity_categories)
    assert len(fr.admin_tiers) >= 3
    assert ".gouv.fr" in fr.example_email
    assert fr.example_phone.startswith("+33")
    assert "Paris" in fr.example_address

    ng = get_country_profile("NG")
    assert ng.default_language == "en"
    assert ".gov.ng" in ng.example_email
    assert ng.example_phone.startswith("+234")
    assert "Abuja" in ng.example_address
