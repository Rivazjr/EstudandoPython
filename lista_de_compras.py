"""
Projeto: Lista de Compras
Um programa simples de linha de comando para gerenciar uma lista de compras,
com preços, quantidades e persistência em arquivo JSON.
"""

import json
import os

ARQUIVO_DADOS = "lista_de_compras.json"


def carregar_lista():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def salvar_lista(lista):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def adicionar_item(lista, nome, quantidade, preco):
    lista.append({
        "nome": nome,
        "quantidade": quantidade,
        "preco": preco,
        "comprado": False,
    })


def remover_item(lista, indice):
    if 0 <= indice < len(lista):
        return lista.pop(indice)
    return None


def marcar_comprado(lista, indice):
    if 0 <= indice < len(lista):
        lista[indice]["comprado"] = True
        return True
    return False


def calcular_total(lista):
    return sum(item["quantidade"] * item["preco"] for item in lista)


def exibir_lista(lista):
    if not lista:
        print("\nSua lista de compras está vazia.\n")
        return

    print("\n--- Lista de Compras ---")
    for i, item in enumerate(lista):
        status = "[X]" if item["comprado"] else "[ ]"
        subtotal = item["quantidade"] * item["preco"]
        print(
            f"{i} {status} {item['nome']} - "
            f"{item['quantidade']}x R$ {item['preco']:.2f} = R$ {subtotal:.2f}"
        )
    print(f"Total: R$ {calcular_total(lista):.2f}\n")


def menu():
    lista = carregar_lista()

    opcoes = {
        "1": "Adicionar item",
        "2": "Remover item",
        "3": "Marcar item como comprado",
        "4": "Exibir lista",
        "5": "Sair",
    }

    while True:
        print("\n=== Menu ===")
        for chave, texto in opcoes.items():
            print(f"{chave}. {texto}")

        escolha = input("Escolha uma opção: ").strip()

        if escolha == "1":
            nome = input("Nome do item: ").strip()
            try:
                quantidade = int(input("Quantidade: "))
                preco = float(input("Preço unitário (R$): "))
            except ValueError:
                print("Quantidade ou preço inválido.")
                continue
            adicionar_item(lista, nome, quantidade, preco)
            salvar_lista(lista)
            print(f"'{nome}' adicionado à lista.")

        elif escolha == "2":
            exibir_lista(lista)
            try:
                indice = int(input("Índice do item a remover: "))
            except ValueError:
                print("Índice inválido.")
                continue
            item = remover_item(lista, indice)
            if item:
                salvar_lista(lista)
                print(f"'{item['nome']}' removido.")
            else:
                print("Índice não encontrado.")

        elif escolha == "3":
            exibir_lista(lista)
            try:
                indice = int(input("Índice do item comprado: "))
            except ValueError:
                print("Índice inválido.")
                continue
            if marcar_comprado(lista, indice):
                salvar_lista(lista)
                print("Item marcado como comprado.")
            else:
                print("Índice não encontrado.")

        elif escolha == "4":
            exibir_lista(lista)

        elif escolha == "5":
            print("Até logo!")
            break

        else:
            print("Opção inválida, tente novamente.")


if __name__ == "__main__":
    menu()
