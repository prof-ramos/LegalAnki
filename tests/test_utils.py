"""Testes para utilitários."""

from legal_anki.utils import (
    escape_html,
    generate_unique_id,
    normalize_tags,
    slugify_tag,
    truncate_text,
)


class TestSlugifyTag:
    """Testes para slugify_tag."""

    def test_remove_accents(self):
        """Remove acentos corretamente."""
        assert slugify_tag("Constituição") == "constituicao"
        assert slugify_tag("Súmula Vinculante") == "sumula_vinculante"
        assert slugify_tag("Ação Direta") == "acao_direta"

    def test_replace_spaces(self):
        """Substitui espaços por underscores."""
        assert slugify_tag("direitos fundamentais") == "direitos_fundamentais"
        assert slugify_tag("  multiplos   espacos  ") == "multiplos_espacos"

    def test_remove_special_chars(self):
        """Remove caracteres especiais."""
        assert slugify_tag("art. 5º") == "art_5o"  # º vira 'o' no NFKD
        assert slugify_tag("CF/88") == "cf88"
        assert slugify_tag("(CESPE)") == "cespe"

    def test_lowercase(self):
        """Converte para lowercase."""
        assert slugify_tag("STF") == "stf"
        assert slugify_tag("CESPE") == "cespe"

    def test_empty_string(self):
        """Retorna vazio para string vazia."""
        assert slugify_tag("") == ""
        assert slugify_tag("   ") == ""

    def test_preserves_hyphen(self):
        """Preserva hífens."""
        assert slugify_tag("controle-concentrado") == "controle-concentrado"


class TestNormalizeTags:
    """Testes para normalize_tags."""

    def test_normalize_list(self):
        """Normaliza lista de tags."""
        tags = ["Direito Constitucional", "STF", "Art. 5º"]
        result = normalize_tags(tags)

        assert "direito_constitucional" in result
        assert "stf" in result
        assert "art_5o" in result  # º vira 'o' no NFKD

    def test_remove_duplicates(self):
        """Remove duplicatas mantendo ordem."""
        tags = ["stf", "STF", "stf"]
        result = normalize_tags(tags)

        assert len(result) == 1
        assert result[0] == "stf"

    def test_remove_empty(self):
        """Remove tags vazias."""
        tags = ["stf", "", "  ", "cespe"]
        result = normalize_tags(tags)

        assert len(result) == 2
        assert "" not in result


class TestGenerateUniqueId:
    """Testes para generate_unique_id."""

    def test_returns_valid_range(self):
        """Retorna ID no range válido do Anki."""
        for _ in range(100):
            id = generate_unique_id()
            assert 1 << 30 <= id < 1 << 31

    def test_returns_different_values(self):
        """Retorna valores diferentes."""
        ids = [generate_unique_id() for _ in range(10)]
        assert len(set(ids)) > 5  # Pelo menos alguns diferentes


class TestEscapeHtml:
    """Testes para escape_html."""

    def test_escape_ampersand(self):
        """Escapa & corretamente."""
        assert escape_html("A & B") == "A &amp; B"

    def test_escape_brackets(self):
        """Escapa < e > corretamente."""
        assert escape_html("<script>") == "&lt;script&gt;"

    def test_escape_quotes(self):
        """Escapa aspas corretamente."""
        assert escape_html('"teste"') == "&quot;teste&quot;"

    def test_empty_string(self):
        """Retorna vazio para string vazia."""
        assert escape_html("") == ""
        assert escape_html(None) == ""


class TestTruncateText:
    """Testes para truncate_text."""

    def test_short_text_unchanged(self):
        """Texto curto não é alterado."""
        text = "Short text"
        assert truncate_text(text, max_length=100) == text

    def test_truncate_long_text(self):
        """Texto longo é truncado."""
        text = "A" * 200
        result = truncate_text(text, max_length=100)

        assert len(result) == 100
        assert result.endswith("...")

    def test_custom_suffix(self):
        """Usa sufixo customizado."""
        text = "A" * 200
        result = truncate_text(text, max_length=100, suffix="[...]")

        assert result.endswith("[...]")

    def test_empty_text(self):
        """Retorna vazio para texto vazio."""
        assert truncate_text("", max_length=100) == ""
        assert truncate_text(None, max_length=100) == ""
