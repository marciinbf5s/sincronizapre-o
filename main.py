import re
import time
import traceback
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import tkinter as tk
from tkinter import ttk, filedialog
import pystray
from PIL import Image, ImageDraw
import os
import fdb

database_path = r"C:\SGBR\Master\BD\BASESGMASTER.FDB"

def conectar_banco():
    """
    Conecta ao Firebird 2.5 e retorna a conexão.
    Em caso de erro, retorna None.
    """
    global database_path
    try:
        user = "SYSDBA"
        password = "masterkey"
        host = "localhost"
        port = 3050

        if not os.path.exists(database_path):
            log(f"❌ Arquivo do banco de dados não encontrado em: {database_path}")
            return None

        con = fdb.connect(
            host=host,
            database=database_path,
            port=port,
            user=user,
            password=password,
            charset='UTF8'
        )
        log("✅ Conectado ao banco de dados com sucesso!")
        return con

    except fdb.DatabaseError as e:
        log(f"❌ Erro ao conectar: {e}")
        return None
    except Exception as e:
        log(f"❌ Erro inesperado: {e}")
        return None

def log(mensagem: str):
    linha = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {mensagem}\n"
    print(linha, end="")
    app_append_log(linha)
    # Salva também em arquivo
    try:
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(linha)
    except Exception as e:
        print(f"Erro ao gravar log em arquivo: {e}")

def obter_cotacao_ouro_24k():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = 'https://www.melhorcambio.com/ouro-hoje'
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        valor_element = soup.find('input', {'id': 'comercial'})
        if not valor_element or 'value' not in valor_element.attrs:
            return None

        valor_ouro = float(valor_element['value'].replace('.', '').replace(',', '.'))
        return {
            'data': datetime.now().strftime('%d/%m/%Y'),
            'valor': valor_ouro,
            'fonte': 'Melhor Câmbio (ouro 24k)'
        }

    except Exception as e:
        log(f"Erro ao obter cotação: {e}")
        log(traceback.format_exc())
        return None

def exibir_cotacao(cotacao):
    if cotacao:
        valor_formatado = f"{cotacao['valor']:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
        log(f"Cotação do Ouro 24K ({cotacao['data']}) - R$ {valor_formatado}/g - Fonte: {cotacao['fonte']}")
        return True
    return False

def obter_preco_venda_referencia(tabela="TESTOQUE", coluna_preco="PRECOVENDA",
                                 coluna_descricao_padrao="PRODUTO",
                                 coluna_referencia_padrao="REFERENCIA"):
    con = conectar_banco()
    if not con:
        return []
    cur = con.cursor()

    cur.execute(f"SELECT r.RDB$FIELD_NAME FROM RDB$RELATION_FIELDS r WHERE r.RDB$RELATION_NAME = '{tabela}'")
    colunas_tabela = [col[0].strip() for col in cur.fetchall()]

    coluna_descricao = next((col for col in colunas_tabela if col.upper() == coluna_descricao_padrao.upper()), None)
    coluna_referencia = next((col for col in colunas_tabela if col.upper() in [coluna_referencia_padrao.upper(), 'REF']), None)

    if not coluna_descricao or not coluna_referencia:
        con.close()
        log("❌ Colunas de descrição ou referência não encontradas na tabela")
        return []

    cur.execute(f"""
        SELECT {coluna_descricao}, {coluna_referencia}, {coluna_preco} 
        FROM {tabela} 
        WHERE {coluna_referencia} IS NOT NULL
    """)

    colunas = [col[0] for col in cur.description]
    resultados = [dict(zip(colunas, row)) for row in cur.fetchall()]
    con.close()

    produtos_formatados = []    
    for produto in resultados:
        ref_original = str(produto[coluna_referencia] or "").strip()

        # só considera se tiver "INDICE"
        if "indice" in ref_original.lower():
            numeros = re.findall(r'\d+(?:\.\d+)?', ref_original)
            numero_ref = float(numeros[0]) if numeros else 0.0

            preco = produto[coluna_preco] or 0.0

            produtos_formatados.append({
                "descricao": produto[coluna_descricao],
                "referencia_original": ref_original,
                "numero_referencia": numero_ref,
                "preco": round(preco, 2)
            })

    return produtos_formatados



class AtualizarPreco:
    def __init__(self):
        self.valor_ouro = 0.0

    def atualizar_cotacao(self):
        cotacao = obter_cotacao_ouro_24k()
        if cotacao:
            self.valor_ouro = cotacao['valor']
        else:
            raise RuntimeError("Não foi possível obter a cotação do ouro.")

    def calcular_novo_preco(self, referencia):
        return round(self.valor_ouro * referencia, 2)

    def atualizar_precos_no_banco(self, produtos):
        con = conectar_banco()
        if not con:
            return
        cur = con.cursor()
        atualizados = 0
        for produto in produtos:
            referencia_num = produto["numero_referencia"]
            referencia_original = produto["referencia_original"]
            novo_preco = self.calcular_novo_preco(referencia_num)
            cur.execute(f"""
                UPDATE TESTOQUE
                SET PRECOVENDA = {novo_preco}
                WHERE REFERENCIA = '{referencia_original}'
            """)
            atualizados += cur.rowcount
        con.commit()
        con.close()
        log(f"Atualizados {atualizados} produtos com a cotação do ouro.")

executando = False
def main():
    global executando
    if executando:
        log("O app já está em execução")
        return

    executando = True
    try:
        atualizador = AtualizarPreco()
        atualizador.atualizar_cotacao()
        exibir_cotacao({"valor": atualizador.valor_ouro, "data": "Agora", "fonte": "Melhor Câmbio"})
        produtos = obter_preco_venda_referencia()
        atualizador.atualizar_precos_no_banco(produtos)
    except Exception as e:
        log(f"Erro inesperado: {e}")
        log(traceback.format_exc())
        log("Tentando reiniciar execução em 5 segundos...")
        threading.Timer(5, main).start()
    finally:
        executando = False

class App:
    def __init__(self, root):
        global database_path
        self.root = root
        self.root.title("Monitor de Atualização de Preços")
        self.root.geometry("800x550")

        # Aba de logs
        self.tabControl = ttk.Notebook(root)
        self.tab_logs = ttk.Frame(self.tabControl)
        self.tabControl.add(self.tab_logs, text='Logs')
        self.tabControl.pack(expand=1, fill="both")

        self.text_logs = tk.Text(self.tab_logs, wrap="word", state="disabled", bg="black", fg="lime")
        self.text_logs.pack(expand=True, fill="both", padx=10, pady=10)

        # Frame de controle
        frame_control = tk.Frame(root)
        frame_control.pack(pady=5)

        self.btn_update = tk.Button(frame_control, text="🔄 Atualizar Manualmente", command=self.executar_manual)
        self.btn_update.pack(side="left", padx=5)

        tk.Label(frame_control, text="Intervalo (h):").pack(side="left")
        self.intervalo_var = tk.StringVar(value="60")
        self.entry_intervalo = tk.Entry(frame_control, width=5, textvariable=self.intervalo_var)
        self.entry_intervalo.pack(side="left", padx=5)

        self.btn_apply = tk.Button(frame_control, text="💾 Aplicar Intervalo", command=self.aplicar_intervalo)
        self.btn_apply.pack(side="left", padx=5)

        # Frame para banco de dados
        frame_db = tk.Frame(root)
        frame_db.pack(pady=5)
        tk.Label(frame_db, text="Caminho do banco:").pack(side="left")
        self.db_var = tk.StringVar(value=database_path)
        self.entry_db = tk.Entry(frame_db, width=50, textvariable=self.db_var)
        self.entry_db.pack(side="left", padx=5)
        tk.Button(frame_db, text="📂 Procurar", command=self.selecionar_banco).pack(side="left", padx=5)

        self.intervalo = 60
        self.agendar_execucao()

        # Minimizar para tray
        self.root.protocol('WM_DELETE_WINDOW', self.minimizar_tray)
        self.criar_tray_icon()
        self.root.withdraw()


    def executar_manual(self):
        if executando:
            log("Aguarde o fim da atualização, para clicar novamente")
            return
        threading.Thread(target=main, daemon=True).start()

    def aplicar_intervalo(self):
        try:
            novo_valor = int(self.intervalo_var.get())
            if novo_valor <= 0:
                raise ValueError
            self.intervalo = int(novo_valor * 3600)
            log(f"Novo intervalo de atualização definido: {novo_valor} horas")
        except ValueError:
            log("Valor inválido para intervalo. Insira um número inteiro maior que 0.")
            

    def agendar_execucao(self):
        threading.Thread(target=main, daemon=True).start()
        self.root.after(self.intervalo * 1000, self.agendar_execucao)

    def append_log(self, mensagem):
        self.text_logs.config(state="normal")
        self.text_logs.insert("end", mensagem)
        self.text_logs.see("end")
        self.text_logs.config(state="disabled")

    def minimizar_tray(self):
        self.root.withdraw()    

    def restaurar_janela(self, icon, item):
        self.root.deiconify()  
        self.root.lift()       
        self.root.focus_force() 

    def sair_app(self, icon, item):
        icon.stop()
        self.root.destroy()

    def criar_tray_icon(self):
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, 64, 64), fill='blue', outline='black')
        draw.arc((12, 12, 52, 52), start=30, end=300, fill='white', width=6)
        draw.polygon([(52, 32), (42, 28), (42, 36)], fill='white')

        menu = pystray.Menu(
            pystray.MenuItem('Abrir', self.restaurar_janela),
            pystray.MenuItem('Sair', self.sair_app)
        )

        icon = pystray.Icon("MonitorPreco", image, "Monitor de Preços", menu)
        threading.Thread(target=icon.run, daemon=True).start()

    def selecionar_banco(self):
        global database_path
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo do banco de dados",
            filetypes=[("Arquivos Firebird FDB", "*.FDB"), ("Todos os arquivos", "*.*")]
        )
        if caminho:
            database_path = caminho
            self.db_var.set(caminho)
            log(f"Caminho do banco atualizado: {caminho}")
            log("⏳ Testando conexão com o banco de dados...")
            conexao_teste = conectar_banco()
            if conexao_teste:
                try:
                    cursor = conexao_teste.cursor()
                    cursor.execute("SELECT 1 FROM RDB$DATABASE")
                    cursor.fetchone()
                    log("✅ Conexão com o banco de dados realizada com sucesso!")
                except Exception as e:
                    log(f"❌ Falha ao testar o banco: {e}")
                finally:
                    conexao_teste.close()
            else:
                log("❌ Não foi possível conectar ao banco com o novo caminho.")

app_instance = None
def app_append_log(msg):
    if app_instance:
        app_instance.append_log(msg)

if __name__ == "__main__":
    while True:
        try:
            root = tk.Tk()
            app_instance = App(root)
            root.mainloop()
        except Exception as e:
            print(f"Erro crítico no app: {e}")
            print(traceback.format_exc())
            print("Reiniciando aplicação em 5 segundos...")
            time.sleep(5)
