"""Testes para o módulo de exportação."""

import json
import tempfile
from pathlib import Path

import pytest


class TestExportToCSV:
    """Testes para exportação CSV."""

    def test_export_csv_to_string(self, sample_cards):
        """Exportação CSV sem arquivo retorna string."""
        from legal_anki.exporters import export_to_csv

        result = export_to_csv(sample_cards, output_path=None)

        assert isinstance(result, str)
        assert "front" in result  # Header
        assert ";" in result  # Separador

    def test_export_csv_to_file(self, sample_cards):
        """Exportação CSV cria arquivo válido."""
        from legal_anki.exporters import export_to_csv

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            result = export_to_csv(sample_cards, Path(tmp.name))

            assert Path(result).exists()
            content = Path(result).read_text(encoding="utf-8")
            assert len(content) > 0

            # Cleanup
            Path(tmp.name).unlink()

    def test_export_csv_without_header(self, sample_cards):
        """Exportação CSV sem header."""
        from legal_anki.exporters import export_to_csv

        result = export_to_csv(sample_cards, output_path=None, include_header=False)

        assert "front" not in result.split("\n")[0]

    def test_export_csv_empty_list_raises_error(self):
        """Exportação com lista vazia deve levantar ExportError."""
        from legal_anki.exporters import ExportError, export_to_csv

        with pytest.raises(ExportError, match="vazia"):
            export_to_csv([])

    def test_export_csv_sanitizes_newlines(self):
        """Newlines no conteúdo são substituídos por espaço."""
        from legal_anki.exporters import export_to_csv
        from legal_anki.models import AnkiCard

        card = AnkiCard(
            front="Pergunta\ncom quebra",
            back="Resposta\nmulti-linha",
            card_type="basic",
            tags=["test"],
            extra=None,
        )
        result = export_to_csv([card], include_header=False)

        # A linha de dados não deve conter \n no conteúdo
        lines = result.strip().split("\n")
        assert len(lines) == 1  # Apenas uma linha de dados
        assert "Pergunta com quebra" in result
        assert "Resposta multi-linha" in result

    def test_export_csv_handles_legal_characters(self):
        """Caracteres jurídicos (§, º, ª) são preservados corretamente."""
        from legal_anki.exporters import export_to_csv
        from legal_anki.models import AnkiCard

        card = AnkiCard(
            front="Art. 5º, § 1º da CF/88",
            back="Os direitos e garantias fundamentais têm aplicação imediata.",
            card_type="basic",
            tags=["cf88", "direitos_fundamentais"],
            extra={"fundamento": "Art. 5º, § 1º, CF/88"},
        )
        result = export_to_csv([card])

        assert "§" in result
        assert "º" in result
        assert "Art. 5º, § 1º" in result


class TestExportToTSV:
    """Testes para exportação TSV."""

    def test_export_tsv_to_string(self, sample_cards):
        """Exportação TSV sem arquivo retorna string."""
        from legal_anki.exporters import export_to_tsv

        result = export_to_tsv(sample_cards, output_path=None)

        assert isinstance(result, str)
        assert "\t" in result  # Tab separator

    def test_export_tsv_to_file(self, sample_cards):
        """Exportação TSV cria arquivo válido."""
        from legal_anki.exporters import export_to_tsv

        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tmp:
            result = export_to_tsv(sample_cards, Path(tmp.name))

            assert Path(result).exists()
            content = Path(result).read_text(encoding="utf-8")
            lines = content.strip().split("\n")
            assert len(lines) == len(sample_cards)

            Path(tmp.name).unlink()


class TestExportToJSON:
    """Testes para exportação JSON."""

    def test_export_json_to_string(self, sample_cards):
        """Exportação JSON sem arquivo retorna string válida."""
        from legal_anki.exporters import export_to_json

        result = export_to_json(sample_cards, output_path=None)

        data = json.loads(result)
        assert "cards" in data
        assert len(data["cards"]) == len(sample_cards)

    def test_export_json_with_metadata(self, sample_cards):
        """Exportação JSON inclui metadata."""
        from legal_anki.exporters import export_to_json

        result = export_to_json(sample_cards, output_path=None, include_metadata=True)

        data = json.loads(result)
        assert "metadata" in data
        assert "skill_version" in data["metadata"]
        assert "generated_at" in data["metadata"]

    def test_export_json_without_metadata(self, sample_cards):
        """Exportação JSON sem metadata."""
        from legal_anki.exporters import export_to_json

        result = export_to_json(sample_cards, output_path=None, include_metadata=False)

        data = json.loads(result)
        assert "metadata" not in data or data.get("metadata") is None


class TestExportToAPKG:
    """Testes para exportação APKG."""

    def test_export_apkg_creates_file(self, sample_cards):
        """Exportação APKG cria arquivo válido."""
        from legal_anki.exporters import export_to_apkg

        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
            result = export_to_apkg(
                sample_cards,
                deck_name="Test Deck",
                output_path=Path(tmp.name),
            )

            assert Path(result).exists()
            assert Path(result).stat().st_size > 0

            Path(tmp.name).unlink()

    def test_export_apkg_base64(self, sample_cards):
        """Exportação APKG base64 retorna string válida."""
        import base64

        from legal_anki.exporters import export_to_apkg_base64

        result = export_to_apkg_base64(sample_cards, deck_name="Test Deck")

        assert isinstance(result, str)
        # Deve ser base64 válido
        decoded = base64.b64decode(result)
        assert len(decoded) > 0


class TestExportCards:
    """Testes para função unificada de exportação."""

    def test_export_cards_csv_default(self, sample_cards):
        """Formato default é CSV."""
        from legal_anki.exporters import export_cards

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            result = export_cards(sample_cards, Path(tmp.name))

            content = Path(result).read_text(encoding="utf-8")
            assert ";" in content

            Path(tmp.name).unlink()

    def test_export_cards_invalid_format(self, sample_cards):
        """Formato inválido levanta exceção."""
        from legal_anki.exporters import ExportError, export_cards

        with pytest.raises(ExportError):
            export_cards(sample_cards, "test.xyz", format="xyz")


class TestMapCardToFields:
    """Testes para mapeamento de cards para campos."""

    def test_map_basic_card(self, sample_card_basic):
        """Mapeia card basic corretamente."""
        from legal_anki.exporters import map_card_to_fields

        fields = map_card_to_fields(sample_card_basic)

        assert len(fields) == 2
        assert fields[0] == sample_card_basic.front
        assert fields[1] == sample_card_basic.back

    def test_map_questao_card(self, sample_cards):
        """Mapeia card questao com todos os campos."""
        from legal_anki.exporters import map_card_to_fields

        questao_card = next(c for c in sample_cards if c.card_type == "questao")
        fields = map_card_to_fields(questao_card)

        assert len(fields) == 6  # Front, Back, Banca, Ano, Cargo, Fundamento
        assert fields[2] == "CESPE"  # Banca
        assert fields[3] == "2023"  # Ano

    def test_map_jurisprudencia_card(self, sample_cards):
        """Mapeia card jurisprudencia com todos os campos."""
        from legal_anki.exporters import map_card_to_fields

        juris_card = next(c for c in sample_cards if c.card_type == "jurisprudencia")
        fields = map_card_to_fields(juris_card)

        assert len(fields) == 6  # Front, Back, Tribunal, Data, Tema, Fundamento
        assert fields[2] == "STF"  # Tribunal
