import os
import sys

# --- Configuração ---
OUTPUT_FILENAME = "consolidated_code.txt"  # Nome do arquivo de saída
PROJECT_ROOT = os.getcwd()  # Assume que o script é executado na raiz do projeto
EXCLUDE_DIRS = {'.env', '.venv', '.test', 'logs'}  # Pastas a serem ignoradas (usar um set é eficiente)
INCLUDE_EXTENSIONS = {'.py'}  # Extensões de arquivo a serem incluídas
# --- Fim da Configuração ---

def consolidate_code():
    """
    Encontra todos os arquivos .ts e .tsx no diretório atual e subdiretórios,
    excluindo os diretórios especificados, e escreve seus caminhos e conteúdos
    em um único arquivo de texto.
    """
    count = 0
    try:
        # Abre o arquivo de saída para escrita com codificação UTF-8
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as outfile:
            print(f"Iniciando a consolidação em '{OUTPUT_FILENAME}'...")
            print(f"Ignorando diretórios: {', '.join(EXCLUDE_DIRS)}")
            print(f"Incluindo extensões: {', '.join(INCLUDE_EXTENSIONS)}")
            print("-" * 30)

            # os.walk percorre a árvore de diretórios de cima para baixo (topdown=True)
            for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT, topdown=True):

                # --- Lógica de Exclusão de Diretórios ---
                # Modifica 'dirnames' *in-place* para não descer nos diretórios excluídos.
                # É importante iterar sobre uma cópia (dirnames[:]) ao modificar a lista original.
                dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

                # Processa os arquivos no diretório atual
                for filename in filenames:
                    # Verifica se a extensão do arquivo está na lista de inclusão
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in INCLUDE_EXTENSIONS:

                        # Constrói o caminho completo e o caminho relativo
                        full_path = os.path.join(dirpath, filename)
                        relative_path = os.path.relpath(full_path, PROJECT_ROOT)

                        # Garante que os separadores de caminho sejam '/' para consistência
                        relative_path_normalized = relative_path.replace(os.sep, '/')

                        try:
                            # Abre o arquivo de origem para leitura com UTF-8
                            with open(full_path, 'r', encoding='utf-8') as infile:
                                content = infile.read()

                            # Escreve o cabeçalho com o caminho do arquivo no arquivo de saída
                            outfile.write(f"########## Path: {relative_path_normalized} ##########\n")
                            # Escreve o conteúdo do arquivo
                            outfile.write(content)
                            # Garante que haja uma nova linha após o conteúdo, se não houver
                            if not content.endswith('\n'):
                                outfile.write('\n')
                            # Escreve um marcador de fim de arquivo para clareza
                            outfile.write(f"########## END FILE: {relative_path_normalized} ##########\n\n")

                            count += 1
                            # Opcional: imprime progresso a cada N arquivos
                            if count % 50 == 0:
                                print(f"Processados {count} arquivos...")

                        except FileNotFoundError:
                            print(f"Aviso: Não foi possível encontrar o arquivo {full_path}. Pulando.", file=sys.stderr)
                        except UnicodeDecodeError:
                            print(f"Aviso: Não foi possível decodificar o arquivo {full_path} como UTF-8. Pulando.", file=sys.stderr)
                        except Exception as e:
                            print(f"Aviso: Erro ao processar o arquivo {full_path}: {e}. Pulando.", file=sys.stderr)

            print("-" * 30)
            print(f"Consolidação concluída. Total de {count} arquivos processados.")
            print(f"O conteúdo foi salvo em '{os.path.join(PROJECT_ROOT, OUTPUT_FILENAME)}'")

    except IOError as e:
        print(f"Erro ao abrir ou escrever no arquivo de saída {OUTPUT_FILENAME}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}", file=sys.stderr)

# Executa a função principal se o script for chamado diretamente
if __name__ == "__main__":
    consolidate_code()