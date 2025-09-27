# 💰 Atualizador de Preços - Ouro 24K

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)

Um aplicativo desktop que atualiza automaticamente os preços de produtos com base na cotação atual do ouro 24K.

## 🚀 Funcionalidades

- ⏳ Atualização em tempo real da cotação do ouro 24K
- 💾 Integração com banco de dados Firebird 2.5
- 🖥️ Interface gráfica amigável
- 📊 Cálculo automático de preços baseado em referências de produtos
- 📝 Logs detalhados das operações

## 🛠️ Pré-requisitos

- Python 3.7 ou superior
- Firebird 2.5
- Bibliotecas Python listadas em `requirements.txt`

## 🔧 Instalação

1. Clone o repositório:
   ```bash
   git clone [URL_DO_REPOSITÓRIO]
   cd buscapreco
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure o caminho do banco de dados no arquivo `main.py`:
   ```python
   database_path = r"C:\SGBR\Master\BD\BASESGMASTER.FDB"
   ```

## 🖥️ Como Usar

1. Execute o aplicativo:
   ```bash
   python main.py
   ```

2. A interface gráfica será aberta mostrando os logs de operação
3. O sistema irá automaticamente:
   - Buscar a cotação atual do ouro 24K
   - Atualizar os preços dos produtos no banco de dados
   - Exibir logs detalhados das operações

## 🔄 Estrutura do Código

- `main.py` - Arquivo principal contendo toda a lógica da aplicação
- `logs.txt` - Arquivo de log gerado automaticamente

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e enviar pull requests.



