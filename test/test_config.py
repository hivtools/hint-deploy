from src import hint_deploy


def test_production_uses_real_email_configuration():
    cfg = hint_deploy.HintConfig("config", "production")
    assert cfg.hint_email_mode == "real"


def test_base_and_staging_use_fake_email_configuration():
    cfg = hint_deploy.HintConfig("config")
    assert cfg.hint_email_mode == "disk"
    cfg = hint_deploy.HintConfig("config", "staging")
    assert cfg.hint_email_mode == "disk"
