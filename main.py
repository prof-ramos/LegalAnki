import argparse
import logging
import sys
from pathlib import Path

from legal_anki.exporters import export_to_csv
from legal_anki.generator import generate_cards

# Configuração de logging básico para console
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="LegalAnki - Gerador de Flashcards Anki para Direito Constitucional",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Argumentos
    parser.add_argument("input", help="Texto de origem ou caminho para um arquivo .txt")
    parser.add_argument(
        "--topic",
        required=True,
        help="Tópico principal dos cards (ex: controle_constitucional)",
    )
    parser.add_argument(
        "--output",
        default="legal_anki_cards.csv",
        help="Caminho do arquivo CSV de saída",
    )
    parser.add_argument(
        "--difficulty",
        choices=["facil", "medio", "dificil"],
        default="medio",
        help="Nível de dificuldade dos cards",
    )
    parser.add_argument(
        "--max-cards",
        type=int,
        default=5,
        help="Número máximo de cards a serem gerados",
    )
    parser.add_argument(
        "--no-legal-basis",
        action="store_false",
        dest="include_legal_basis",
        help="Não obriga a inclusão de fundamento legal nos cards",
    )
    # include_legal_basis já tem default True via action="store_false" + dest.
    # Removendo set_defaults redundante.

    args = parser.parse_args()

    if args.max_cards < 1 or args.max_cards > 1000:
        parser.error("--max-cards deve estar entre 1 e 1000")

    # 1. Determina o conteúdo de entrada
    input_path = Path(args.input)
    if input_path.is_file():
        try:
            content = input_path.read_text(encoding="utf-8")
            logger.info("Lendo conteúdo do arquivo: %s", args.input)
        except Exception as e:
            logger.error("Erro ao ler arquivo %s: %s", args.input, e, exc_info=True)
            sys.exit(1)
    else:
        content = args.input
        logger.info("Processando texto fornecido diretamente via CLI")

    # 2. Gera os cards via LLM
    logger.info(
        "Iniciando geração de até %d cards para o tópico: %s",
        args.max_cards,
        args.topic,
    )
    try:
        cards = generate_cards(
            text=content,
            topic=args.topic,
            difficulty=args.difficulty,
            include_legal_basis=args.include_legal_basis,
            max_cards=args.max_cards,
        )
    except Exception:
        logger.exception("Falha na geração de cards")
        sys.exit(1)

    # 3. Exporta para CSV
    try:
        output_file = export_to_csv(cards, output_path=args.output)
        logger.info("Sucesso! %d cards exportados para: %s", len(cards), output_file)
    except Exception:
        logger.exception("Erro ao exportar cards")
        sys.exit(1)


if __name__ == "__main__":
    main()
