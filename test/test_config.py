import pytest

from src import hint_cli, hint_deploy


def test_production_uses_real_adr():
    cfg = hint_deploy.HintConfig("config", "production")
    assert cfg.hint_adr_url == "https://adr.unaids.org/"


def test_real_adr_optional():
    cfg = hint_deploy.HintConfig("config")
    assert cfg.hint_adr_url is None


def test_production_and_staging_use_real_email_configuration():
    cfg = hint_deploy.HintConfig("config", "production")
    assert cfg.hint_email_mode == "real"
    cfg = hint_deploy.HintConfig("config", "staging")
    assert cfg.hint_email_mode == "real"


def test_base_uses_fake_email_configuration():
    cfg = hint_deploy.HintConfig("config")
    assert cfg.hint_email_mode == "disk"


def test_proxy_url_drops_port_appropriately():
    assert hint_deploy.proxy_url("example.com", 443) == \
        "https://example.com"
    assert hint_deploy.proxy_url("example.com", 1443) == \
        "https://example.com:1443"


def test_load_and_reload_config():
    path = "config"
    config = "production"
    cfg = hint_deploy.HintConfig(path, config)
    cfg.hint_tag = "develop"
    hint_cli.save_config(path, config, cfg)

    hint_cli.read_config(path)

    config_name, config_value = hint_cli.load_config(path, None)
    assert config_value.hint_tag == "master"
    assert config_name == "production"
    hint_cli.remove_config(path)


def test_production_uses_persistant_keypair():
    cfg = hint_deploy.HintConfig("config", "production")
    assert cfg.hint_keypair is not None


def test_staging_uses_transient_keypair():
    cfg = hint_deploy.HintConfig("config", "staging")
    assert cfg.hint_keypair is None


def test_keypair_allows_missing_key():
    dat = {"app": {"a": 1}}
    assert hint_deploy.keypair(dat, ["app", "key"]) is None


def test_keypair_loads_keypair():
    public = "VAULT:/secret/path:public"
    private = "VAULT:/secret/path:private"
    dat = {"app": {"a": 1, "key": {"public": public, "private": private}}}
    pair = hint_deploy.keypair(dat, ["app", "key"])
    assert pair == {"public": public, "private": private}


def test_keypair_throws_if_half_given():
    public = "VAULT:/secret/path:public"
    dat = {"app": {"a": 1, "k": {"public": public}}}
    msg = "Provide either both or neither 'app:k:public' and 'app:k:private'"
    with pytest.raises(Exception, match=msg):
        hint_deploy.keypair(dat, ["app", "k"])
