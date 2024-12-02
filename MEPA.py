import os
import sys
#import msvcrt  # Módulo exclusivo para Windows

# Função para aguardar qualquer tecla
def esperar_tecla():
    """Aguarda qualquer tecla no Windows ou Linux."""
    if os.name == 'nt':  # Sistema Windows
        import msvcrt
        msvcrt.getch()
    else:  # Sistema Linux ou macOS
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            
# Variáveis globais
arquivo_carregado = None
codigo = []  # Armazena as instruções carregadas
labels = {}  # Dicionário para associar labels aos endereços
memoria = {}  # Memória virtual para armazenar variáveis
pilha = []  # Pilha para operações
modificacoes_nao_salvas = False  # Indica se houve alterações não salvas
modo_debug = False
pc_debug = 0  # Program Counter para o modo DEBUG


def shell_interativo():
    """Loop interativo para interpretar comandos."""
    global arquivo_carregado, codigo, modificacoes_nao_salvas
    while True:
        comando = input("> ").strip()
        if not comando:
            continue
        
        if comando.upper() == "EXIT":
            # Verifica se há um arquivo carregado e se há modificações não salvas
            if arquivo_carregado and modificacoes_nao_salvas:
                print(f"Arquivo atual ('{arquivo_carregado}') contém alterações não salvas.")
                resposta = input("Deseja salvar (S/N)? ").strip().lower()
                if resposta == 's':
                    save()
            print("Encerrando o programa.")
            break

        elif comando.upper().startswith("LOAD "):
            caminho = comando[5:].strip()
            if arquivo_carregado:  # Se já tiver um arquivo carregado
                # Pergunta se deseja salvar o arquivo atual antes de carregar o novo
                if modificacoes_nao_salvas:
                    print(f"Arquivo atual ('{arquivo_carregado}') contém alterações não salvas.")
                    resposta = input("Deseja salvar (S/N)? ").strip().lower()
                    if resposta == 's':
                        save()

            if os.path.exists(caminho):
                try:
                    load(caminho)
                    print(f"Arquivo '{caminho}' carregado com sucesso.")
                except Exception as e:
                    print(f"Erro ao carregar o arquivo: {e}")
            else:
                print(f"Erro: arquivo '{caminho}' não encontrado.")
                
        elif comando.upper() == "SAVE":
            save()
        elif comando.upper() == "LIST":
            list()
        elif comando.upper() == "RUN":
            run()
        elif comando.upper().startswith("INS "):
            ins_linha(comando)
        elif comando.upper().startswith("DEL "):
            del_linha(comando)
        elif comando.upper() == "DEBUG":
            iniciar_debug()
        elif comando.upper() == "NEXT":
            avancar_debug()
        elif comando.upper() == "STACK":
            exibir_pilha()
        elif comando.upper() == "STOP":
            parar_debug()
        else:
            print("Erro: comando inválido.")

def load(caminho):
    """Carrega o arquivo MEPA e armazena suas instruções."""
    global arquivo_carregado, codigo, labels, modificacoes_nao_salvas
    if arquivo_carregado and modificacoes_nao_salvas:
        print(f"Arquivo atual ('{arquivo_carregado}') contém alterações não salvas.")
        resposta = input("Deseja salvar (S/N)? ").strip().lower()
        if resposta == 's':
            save()  # Chama a função de salvar o arquivo atual

    # Carregar o novo arquivo
    arquivo_carregado = caminho
    codigo = []
    labels = {}

    try:
        with open(caminho, 'r') as file:
            linhas = file.readlines()

        endereco = 10  # Endereços começam em 10 e incrementam de 10 em 10
        for linha in linhas:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue  # Ignora comentários e linhas em branco

            if ":" in linha:  # Processa labels
                label, instrucao = linha.split(":", 1)
                labels[label.strip()] = endereco
                linha = f"{label.strip()}: {instrucao.strip()}"

            codigo.append((endereco, linha))
            endereco += 10
        
        modificacoes_nao_salvas = False  # Não há alterações após carregar
    except Exception as e:
        print(f"Erro ao carregar o arquivo: {e}")


def list():
    """Lista as instruções do arquivo carregado, 20 linhas por vez."""
    global codigo
    if not codigo:
        print("Nenhum arquivo carregado.")
        return

    pagina = 0
    linhas_por_pagina = 20
    total_linhas = len(codigo)

    while pagina * linhas_por_pagina < total_linhas:
        inicio = pagina * linhas_por_pagina
        fim = min(inicio + linhas_por_pagina, total_linhas)
        
        for endereco, instrucao in codigo[inicio:fim]:
            # Exibe a instrução preservando a label, se houver
            print(f"{endereco} {instrucao}")

        pagina += 1
        if fim < total_linhas:
            print("Pressione qualquer tecla para continuar...")
            esperar_tecla()  # Usa msvcrt.getch()


def run():
    """Executa o código MEPA carregado."""
    global codigo, memoria, pilha, labels
    if not codigo:
        print("Erro: nenhum código carregado na memória.")
        return

    memoria = []
    pilha = []
    pc = 0  # Program counter, índice da instrução atual

    while pc < len(codigo):
        endereco, instrucao = codigo[pc]
        partes = instrucao.split()
        comando = partes[0].upper()

        # Verifica se o argumento é uma label (como L1, L2, etc.)
        if len(partes) > 1:
            argumento = partes[1].upper()

            # Verifica se o argumento é uma label (tipo L1, L2, etc.)
            if argumento in labels:
                # Se for uma label, buscamos seu endereço
                argumento = labels[argumento]
            else:
                # Se não for uma label, tenta converter para inteiro
                try:
                    argumento = int(argumento)
                except ValueError:
                    # Se não for possível converter, mantém o valor como string
                    pass
        else:
            argumento = None

        if comando == "NADA":
            # Não faz nada, apenas avança para a próxima instrução
            pc += 1
            continue

        if comando == "INPP":
            memoria = [0] * 100  # Inicializa a memória com 100 posições
        elif comando == "AMEM":
            memoria.extend([0] * argumento)
        elif comando == "DMEM":
            memoria = memoria[:-argumento]
        elif comando == "CRCT":
            pilha.append(argumento)
        elif comando == "CRVL":
            pilha.append(memoria[argumento])
        elif comando == "ARMZ":
            memoria[argumento] = pilha.pop()
        elif comando == "SOMA":
            b = pilha.pop()
            a = pilha.pop()
            pilha.append(a + b)
        elif comando == "MULT":
            b = pilha.pop()
            a = pilha.pop()
            pilha.append(a * b)
        elif comando == "CMEG":
            b = pilha.pop()
            a = pilha.pop()
            pilha.append(1 if a <= b else 0)
        elif comando == "DVSF":
            if pilha.pop() == 0:
                # Caso DVSF, faz o salto para o endereço da label (se a pilha for 0)
                pc = next((i for i, (addr, _) in enumerate(codigo) if addr == argumento), pc)
                continue
        elif comando == "DSVS":
            # Caso DSVS, faz o salto sem verificar a pilha
            pc = next((i for i, (addr, _) in enumerate(codigo) if addr == argumento), pc)
            continue
        elif comando == "IMPR":
            print(pilha.pop())
        elif comando == "PARA":
            break
        pc += 1


def ins_linha(comando):
    """Insere uma linha no código carregado."""
    global codigo, modificacoes_nao_salvas
    partes = comando.split(maxsplit=2)
    numero_linha = int(partes[1])
    nova_instrucao = partes[2]

    # Verifica se a linha já existe
    for i, (endereco, instrucao) in enumerate(codigo):
        if endereco == numero_linha:
            codigo[i] = (endereco, nova_instrucao)  # Substitui a linha
            print(f"Linha substituída:\nDe {endereco} {instrucao} Para {endereco} {nova_instrucao}")
            modificacoes_nao_salvas = True
            return
    # Se a linha não existe, insere
    codigo.append((numero_linha, nova_instrucao))
    codigo.sort()  # Organiza as instruções pela ordem de endereço
    print(f"Linha inserida:\n{numero_linha} {nova_instrucao}")
    modificacoes_nao_salvas = True


def del_linha(comando):
    """Remove uma linha do código carregado."""
    global codigo, modificacoes_nao_salvas
    numero_linha = int(comando.split()[1])

    for i, (endereco, instrucao) in enumerate(codigo):
        if endereco == numero_linha:
            codigo.pop(i)
            print(f"Linha removida:\n{numero_linha} {instrucao}")
            modificacoes_nao_salvas = True
            return
    print(f"Erro: Linha {numero_linha} inexistente.")

def save():
    """Salva o código-fonte no arquivo carregado."""
    global arquivo_carregado, codigo, modificacoes_nao_salvas
    if arquivo_carregado:
        try:
            with open(arquivo_carregado, 'w') as file:
                for endereco, instrucao in codigo:
                    # Salvando apenas a instrução, sem o endereço
                    file.write(f"{instrucao}\n")
            modificacoes_nao_salvas = False
            print(f"Arquivo '{arquivo_carregado}' salvo com sucesso.")
        except Exception as e:
            print(f"Erro ao salvar o arquivo: {e}")
    else:
        print("Erro: Nenhum arquivo carregado.")

def iniciar_debug():
    """Inicia o modo de depuração."""
    global modo_debug, pc_debug, memoria, pilha

    if not codigo:
        print("Erro: nenhum código carregado para depuração.")
        return

    modo_debug = True
    pc_debug = 0  # Program counter no início do código
    memoria = [0] * 100  # Inicializa a memória
    pilha = []  # Inicializa a pilha vazia

    print("Iniciando modo de depuração:")
    print_instrucao_atual()
    pc_debug += 1

def print_instrucao_atual():
    """Exibe a instrução atual no modo de depuração."""
    global pc_debug, codigo
    if pc_debug < len(codigo):
        endereco, instrucao = codigo[pc_debug]
        print(f"{endereco} {instrucao}")
    else:
        print("Fim do código.")

def avancar_debug():
    """Executa a próxima instrução no modo de depuração."""
    global modo_debug, pc_debug, memoria, pilha, codigo

    if not modo_debug:
        print("Erro: O programa não está no modo de depuração.")
        return

    if pc_debug >= len(codigo):
        print("Fim do código. Modo de depuração finalizado.")
        modo_debug = False
        return

    endereco, instrucao = codigo[pc_debug]
    partes = instrucao.split()
    comando = partes[0].upper()
    argumento = None

    if len(partes) > 1:
        try:
            argumento = int(partes[1])
        except ValueError:
            print(f"Erro: Argumento inválido na instrução '{instrucao}'.")
            return

    # Exibe a instrução atual
    print(f"{endereco} {instrucao}")

    # Ignora a execução de INPP após a primeira execução
    if comando == "INPP" and pc_debug == 0:
        # Inicializa a memória e pilha apenas uma vez
        memoria = [0] * 100
        pilha = []
        pc_debug += 1  # Avança para a próxima instrução
        return

    # Executa a instrução no modo de depuração
    if comando == "AMEM":
        # Adiciona `argumento + 1` posições na pilha inicializadas como 0
        for _ in range(argumento):
            pilha.append(0)
    elif comando == "DMEM":
        if argumento <= len(pilha):
            for _ in range(argumento):
                pilha.pop()  # Remove elementos do topo da pilha
        else:
            print("Erro: Tentativa de desalocar mais memória do que existe.")
    elif comando == "CRCT":
        pilha.append(argumento)
    elif comando == "CRVL":
        if 0 <= argumento < len(memoria):
            pilha.append(memoria[argumento])
        else:
            print(f"Erro: Índice de memória inválido ({argumento}).")
    elif comando == "ARMZ":
        # ARMAZENA o valor do topo da pilha na posição especificada e remove o topo
        if pilha:
            if 0 <= argumento < len(pilha):
                # Substitui o valor na posição indicada com o valor do topo da pilha
                pilha[argumento] = pilha.pop()  # Remove o topo e armazena na posição
            else:
                print(f"Erro: Índice de pilha inválido ({argumento}).")
        else:
            print("Erro: Tentativa de ARMZ com pilha vazia.")
    elif comando == "SOMA":
        if len(pilha) >= 2:
            b = pilha.pop()
            a = pilha.pop()
            pilha.append(a + b)
        else:
            print("Erro: Pilha com menos de dois elementos para SOMA.")
    elif comando == "SUBT":
        if len(pilha) >= 2:
            b = pilha.pop()
            a = pilha.pop()
            pilha.append(a - b)
        else:
            print("Erro: Pilha com menos de dois elementos para SUBT.")
    elif comando == "MULT":
        if len(pilha) >= 2:
            b = pilha.pop()
            a = pilha.pop()
            pilha.append(a * b)
        else:
            print("Erro: Pilha com menos de dois elementos para MULT.")
    elif comando == "DIVI":
        if len(pilha) >= 2:
            b = pilha.pop()
            if b == 0:
                print("Erro: Divisão por zero.")
                pilha.append(0)  # Valor de fallback
            else:
                a = pilha.pop()
                pilha.append(a // b)
        else:
            print("Erro: Pilha com menos de dois elementos para DIVI.")
    elif comando == "INVR":
        if pilha:
            pilha.append(-pilha.pop())
        else:
            print("Erro: Tentativa de INVR com pilha vazia.")
    elif comando == "PARA":
        print("Instrução PARA encontrada. Modo de depuração finalizado.")
        modo_debug = False
        return
    elif comando == "IMPR":
        if pilha:
            print(f"Valor no topo da pilha: {pilha[-1]}")
        else:
            print("Erro: Tentativa de IMPR com pilha vazia.")
    elif comando == "NADA":
        pass  # Nenhuma ação necessária
    else:
        print(f"Comando {comando} não implementado no modo de depuração.")

    # Move para a próxima instrução
    pc_debug += 1

def exibir_pilha():
    """Exibe o conteúdo da pilha."""
    if not pilha:
        print("A pilha está vazia.")
    else:
        print("Conteúdo da pilha:")
        for i, valor in enumerate(pilha):
            print(f"{i}: {valor}")



def parar_debug():
    """Interrompe o modo de depuração."""
    global modo_debug
    if modo_debug:
        print("Modo de depuração finalizado!")
        modo_debug = False
    else:
        print("Erro: O programa não está no modo de depuração.")



# Inicializa o shell interativo
if __name__ == "__main__":
    shell_interativo()
