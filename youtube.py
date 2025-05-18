from pytubefix import YouTube                      # Importa a classe principal para manipular vídeos do YouTube
from pytubefix.cli import on_progress              # Importa o callback de progresso para mostrar o andamento dos downloads
from slugify import slugify                        # Transforma o título do vídeo em um nome de arquivo seguro
import os
from pathlib import Path                           # Para manipulação segura de diretórios e arquivos
import sys
import subprocess                                  # Usado para executar o FFmpeg (fusão de áudio e vídeo)
from time import sleep                             # Para criar delays (animação de loading)

def clear_screen():
    """
    Limpa a tela do terminal de forma multiplataforma (Windows ou Unix).
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """
    Exibe um banner estilizado com informações do programa.
    """
    banner = """
    ╔══════════════════════════════════════════╗
    ║          YouTube Video Downloader        ║
    ║                                          ║
    ║   Desenvolvido por [Rosonatt Ferreira]   ║
    ║              Versão 2.0                  ║
    ╚══════════════════════════════════════════╝
    """
    print(banner)


def loading_animation(text):
    """
    Exibe uma animação de carregamento giratória.
    
    Parâmetro:
        text (str): Texto a ser exibido antes da animação.
    """
    chars = "/—\\|"
    for _ in range(20):  # repete a animação por um tempo fixo (~2 segundos)
        for char in chars:
            sys.stdout.write(f'\r{text} {char}')
            sys.stdout.flush()
            sleep(0.1)


def get_video_info(url):
    """
    Recebe uma URL e retorna o objeto do vídeo e suas informações principais.

    Parâmetro:
        url (str): URL do vídeo no YouTube.

    Retorna:
        (yt, info): objeto YouTube e dicionário com informações do vídeo.
    """
    try:
        yt = YouTube(url, on_progress_callback=on_progress)
        info = {
            'title': yt.title,
            'author': yt.author,
            'length': f"{int(yt.length/60)}:{int(yt.length%60):02d}",
            'views': f"{yt.views:,}",
            'publish_date': yt.publish_date.strftime("%d/%m/%Y")
        }
        return yt, info
    except Exception as e:
        print(f"\nErro ao obter informações do vídeo: {e}")
        sys.exit(1)


def display_video_info(info):
    """
    Exibe informações do vídeo no terminal de forma formatada.

    Parâmetro:
        info (dict): Dicionário com informações do vídeo.
    """
    print("\n╔════════════ Informações do Vídeo ════════════╗")
    print(f"║ Título: {info['title'][:40]}{'...' if len(info['title']) > 40 else ''}")
    print(f"║ Canal: {info['author']}")
    print(f"║ Duração: {info['length']}")
    print(f"║ Visualizações: {info['views']}")
    print(f"║ Data de publicação: {info['publish_date']}")
    print("╚═══════════════════════════════════════════════╝")


def select_resolution(video_streams):
    """
    Lista as resoluções disponíveis e permite ao usuário escolher uma.

    Parâmetro:
        video_streams: Lista de streams de vídeo disponíveis.

    Retorna:
        (str): Resolução escolhida pelo usuário.
    """
    resolucoes = []
    print("\n═══════════ Resoluções Disponíveis ═══════════")
    for stream in video_streams:
        resolucao = stream.resolution
        if resolucao and resolucao not in resolucoes:
            resolucoes.append(resolucao)
            print(f"  [{len(resolucoes)}] {resolucao}")
    print("═════════════════════════════════════════════")

    while True:
        try:
            opcao = int(input("\nSelecione a resolução desejada [número]: ")) - 1
            if 0 <= opcao < len(resolucoes):
                return resolucoes[opcao]
            print("Opção inválida. Tente novamente.")
        except ValueError:
            print("Por favor, digite um número válido.")


def download_and_merge(yt, video_stream, audio_stream, destino):
    """
    Faz o download dos arquivos de vídeo e áudio separadamente e os mescla usando FFmpeg.

    Parâmetros:
        yt: Objeto YouTube.
        video_stream: Stream de vídeo selecionado.
        audio_stream: Melhor stream de áudio disponível.
        destino: Caminho de destino para salvar os arquivos.
    """
    safe_title = slugify(yt.title)
    video_path = destino / f"{yt.video_id}_video.mp4"
    audio_path = destino / f"{yt.video_id}_audio.mp4"
    output_path = destino / f"{safe_title}_{video_stream.resolution}.mp4"

    try:
        loading_animation("Baixando vídeo")
        video_stream.download(output_path=destino, filename=video_path.name)
        
        loading_animation("Baixando áudio")
        audio_stream.download(output_path=destino, filename=audio_path.name)

        print("\nMesclando arquivos... ")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",              # Copia o vídeo sem reencodificar
            "-c:a", "aac",               # Codifica o áudio para AAC
            "-strict", "experimental",
            str(output_path)
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        # Remove arquivos temporários
        os.remove(video_path)
        os.remove(audio_path)
        
        print("\n✔ Download concluído com sucesso!")
        print(f"📁 Arquivo salvo em: {output_path}")
        
    except Exception as e:
        print(f"\n❌ Erro durante o processo: {e}")
        sys.exit(1)


def main():
    """
    Função principal que orquestra todo o processo:
    - Limpa a tela
    - Mostra banner
    - Solicita URL
    - Obtém info e exibe
    - Filtra streams
    - Deixa o usuário escolher a resolução
    - Faz download e mescla os arquivos
    """
    clear_screen()
    print_banner()
    
    url = input("\n📺 Digite a URL do vídeo: ").strip()
    destino = Path.home() / "Videos"  # Salva na pasta padrão "Vídeos" do sistema
    
    loading_animation("Obtendo informações do vídeo")
    yt, info = get_video_info(url)
    display_video_info(info)
    
    # Filtra apenas vídeos adaptativos em mp4 (sem áudio)
    video_streams = yt.streams.filter(
        adaptive=True, 
        only_video=True, 
        file_extension='mp4'
    ).order_by('resolution').desc()
    
    resolucao_escolhida = select_resolution(video_streams)
    
    video_stream = yt.streams.filter(
        res=resolucao_escolhida, 
        only_video=True, 
        file_extension='mp4'
    ).first()
    
    audio_stream = yt.streams.filter(
        only_audio=True, 
        file_extension='mp4'
    ).order_by('abr').desc().first()
    
    if not all([video_stream, audio_stream]):
        print("\n❌ Erro: Streams não encontrados")
        sys.exit(1)
        
    download_and_merge(yt, video_stream, audio_stream, destino)


# Execução principal
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
        sys.exit(0)
