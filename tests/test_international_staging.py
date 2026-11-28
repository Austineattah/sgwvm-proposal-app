from pathlib import Path
import pytest
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

def test_germany_profile_and_fr_de_onboarding_benefit_translations():
    from src.i18n_staging import LANGUAGE_LABELS, TRANSLATIONS, get_text, normalize_language_code
    from src.international_staging import COUNTRY_PROFILES, format_country_currency, get_country_profile

    assert "DE" in COUNTRY_PROFILES
    de_profile = get_country_profile("DE")
    assert de_profile.code == "DE"
    assert de_profile.currency_code == "EUR"
    assert de_profile.default_language == "de"
    assert "de" in de_profile.supported_languages
    assert "en" in de_profile.supported_languages
    assert len(de_profile.entity_categories) >= 5
    assert len(de_profile.admin_tiers) >= 4
    assert "EUR" in format_country_currency(1500, "DE")

    fr_profile = get_country_profile("FR")
    assert fr_profile.code == "FR"
    assert fr_profile.currency_code == "EUR"
    assert fr_profile.default_language == "fr"

    assert normalize_language_code("de") == "de"
    assert normalize_language_code("fr") == "fr"
    assert "de" in LANGUAGE_LABELS
    assert "fr" in LANGUAGE_LABELS

    for key in [
        "hero_subtitle",
        "onboarding_step1_heading",
        "entity_category_label",
        "org_name_label",
        "benefits_button_label",
        "about_org_button_label",
        "benefits_heading",
        "benefit_volume_title",
        "benefit_reputation_title",
        "benefit_governance_title",
    ]:
        fr_val = get_text(key, "fr")
        de_val = get_text(key, "de")
        en_val = get_text(key, "en")
        assert fr_val and fr_val != key
        assert de_val and de_val != key
        assert en_val and en_val != key
        assert fr_val != en_val
        assert de_val != en_val

    fr_cats = TRANSLATIONS.get("fr", {}).get("entity_categories")
    de_cats = TRANSLATIONS.get("de", {}).get("entity_categories")
    en_cats = TRANSLATIONS.get("en", {}).get("entity_categories")
    assert isinstance(fr_cats, list) and len(fr_cats) >= 4
    assert isinstance(de_cats, list) and len(de_cats) >= 4
    assert isinstance(en_cats, list) and len(en_cats) >= 4
    assert fr_cats != en_cats
    assert de_cats != en_cats

@pytest.mark.parametrize("country_code", ["FR", "DE"])
def test_onboarding_country_selection_apptest(country_code: str) -> None:
    st_testing = pytest.importorskip("streamlit.testing.v1")
    AppTest = st_testing.AppTest

    from src.i18n_staging import TRANSLATIONS, get_text
    from src.international_staging import get_country_profile

    profile = get_country_profile(country_code)
    lang = profile.default_language

    app_entry = Path(__file__).resolve().parent.parent / "app.py"
    at = AppTest.from_file(str(app_entry), default_timeout=20)
    at.session_state["active_country_code"] = country_code
    at.session_state["active_language_code"] = lang
    at.run()

    for sb in at.selectbox:
        if any(opt in sb.options for opt in TRANSLATIONS.get(lang, {}).get("entity_categories", ())) is False:
            if getattr(sb, "key", None) == "nv_onboarding_country_select" and country_code in sb.options:
                sb.set_value(country_code)
                at.run()
                break

    assert not at.exception, f"Unexpected exception for {country_code}: {at.exception}"
    assert at.session_state.get("active_language_code") == lang

    expected_cats = TRANSLATIONS.get(lang, {}).get("entity_categories") or list(profile.entity_categories)
    found_expected_cat = False
    for sb in at.selectbox:
        if any(opt in sb.options for opt in expected_cats):
            for opt in expected_cats:
                assert opt in sb.options
            found_expected_cat = True
            break
    assert found_expected_cat, f"Expected localized entity_categories for {country_code} ({lang}) in selectbox options"

    btn_label = get_text("benefits_button_label", lang)
    clicked_benefits = False
    for btn in at.button:
        if btn_label in (getattr(btn, "label", "") or ""):
            btn.click()
            clicked_benefits = True
            break
    if not clicked_benefits:
        at.session_state["onboarding_showcase_tab"] = "benefits"
    at.run()
    assert not at.exception

    expected_heading = get_text("benefits_heading", lang)
    rendered_md = " ".join(getattr(m, "value", "") for m in at.markdown)
    assert expected_heading in rendered_md
