import pytest

from app.document_templates import TemplateNotFoundError, empty_fields, load_manifest, load_template


def test_load_manifest_returns_all_eight_templates():
    manifest = load_manifest()
    assert len(manifest) == 8
    assert {entry["id"] for entry in manifest} == {
        "nda",
        "rental_agreement",
        "employment_offer_letter",
        "power_of_attorney",
        "cease_and_desist_letter",
        "last_will_and_testament",
        "service_agreement",
        "affidavit",
    }


@pytest.mark.parametrize(
    "template_id",
    [entry["id"] for entry in load_manifest()],
)
def test_load_template_matches_manifest_entry(template_id):
    template = load_template(template_id)
    assert template["id"] == template_id
    assert template["fields"]


def test_load_template_raises_for_unknown_id():
    with pytest.raises(TemplateNotFoundError):
        load_template("does-not-exist")


def test_empty_fields_covers_every_field_key():
    fields = empty_fields("nda")
    template = load_template("nda")
    assert set(fields.keys()) == {field["key"] for field in template["fields"]}
    assert all(value is None for value in fields.values())
