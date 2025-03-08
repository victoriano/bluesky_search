#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky Posts Fetcher

Este script permite obtener los posts recientes de una lista de usuarios de Bluesky.
Utiliza la biblioteca atproto para interactuar con la API de AT Protocol.
"""

import os
import json
import argparse
import datetime
from typing import List, Dict, Any, Optional
from atproto import Client

# Importaciones para exportación de datos
try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    # Intentar instalar polars automáticamente usando uv
    try:
        import subprocess
        print("Instalando polars automáticamente usando uv...")
        subprocess.check_call(["uv", "pip", "install", "polars"])
        import polars as pl
        POLARS_AVAILABLE = True
        print("✅ Polars instalado correctamente")
    except Exception as e:
        print(f"❌ Error al instalar polars: {str(e)}")
        print("Para instalar manualmente, ejecute: uv pip install -r requirements.txt")

class BlueskyPostsFetcher:
    """Clase para obtener posts de usuarios de Bluesky."""
    
    def __init__(self, username: str = None, password: str = None):
        """
        Inicializa el cliente de Bluesky.
        
        Args:
            username: Nombre de usuario o correo electrónico para autenticación
            password: Contraseña para autenticación
        """
        self.client = Client()
        if username and password:
            self.login(username, password)
    
    def login(self, username: str, password: str) -> bool:
        """
        Inicia sesión en Bluesky.
        
        Args:
            username: Nombre de usuario o correo electrónico
            password: Contraseña
            
        Returns:
            bool: True si la autenticación fue exitosa, False en caso contrario
        """
        try:
            self.client.login(username, password)
            print(f"✅ Autenticación exitosa como {username}")
            return True
        except Exception as e:
            print(f"❌ Error de autenticación: {str(e)}")
            return False
    
    def get_user_posts(self, handle: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtiene los posts recientes de un usuario.
        
        Args:
            handle: Nombre de usuario de Bluesky (con o sin @)
            limit: Número máximo de posts a obtener
            
        Returns:
            List[Dict]: Lista de posts con información relevante
        """
        # Asegurarse de que el handle no tenga @ al inicio
        if handle.startswith('@'):
            handle = handle[1:]
        
        try:
            # Obtener el perfil del usuario
            profile = self.client.get_profile(actor=handle)
            
            # Obtener los posts del usuario
            author_feed = self.client.get_author_feed(actor=handle, limit=limit)
            
            # Procesar los posts
            posts = []
            for feed_view in author_feed.feed:
                post = feed_view.post
                
                # Extraer información relevante
                post_data = {
                    'uri': post.uri,
                    'cid': post.cid,
                    'author': {
                        'did': post.author.did,
                        'handle': post.author.handle,
                        'display_name': getattr(post.author, 'display_name', post.author.handle)
                    },
                    'text': post.record.text,
                    'created_at': post.record.created_at,
                    'likes': getattr(post, 'like_count', 0),
                    'reposts': getattr(post, 'repost_count', 0),
                    'replies': getattr(post, 'reply_count', 0)
                }
                
                # Añadir imágenes si existen
                if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images'):
                    post_data['images'] = [img.alt for img in post.record.embed.images]
                
                posts.append(post_data)
            
            print(f"✅ Obtenidos {len(posts)} posts de @{handle}")
            return posts
        
        except Exception as e:
            print(f"❌ Error al obtener posts de @{handle}: {str(e)}")
            return []
    
    def get_posts_from_list(self, handles: List[str], limit_per_user: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtiene posts de una lista de usuarios.
        
        Args:
            handles: Lista de nombres de usuario de Bluesky
            limit_per_user: Número máximo de posts por usuario
            
        Returns:
            Dict: Diccionario con los posts de cada usuario
        """
        results = {}
        
        for handle in handles:
            clean_handle = handle.strip()
            if clean_handle:
                posts = self.get_user_posts(clean_handle, limit_per_user)
                if posts:
                    results[clean_handle] = posts
        
        return results
    
    def save_results_to_json(self, results: Dict[str, List[Dict[str, Any]]], filename: str = None) -> str:
        """
        Guarda los resultados en un archivo JSON.
        
        Args:
            results: Diccionario con los resultados
            filename: Nombre del archivo (opcional)
            
        Returns:
            str: Ruta del archivo guardado
        """
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bluesky_posts_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Resultados guardados en {filename}")
        return filename
        
    def _flatten_results(self, results: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Convierte los resultados anidados a una estructura plana para exportación a CSV/Parquet.
        
        Args:
            results: Diccionario con los resultados
            
        Returns:
            List[Dict]: Lista de posts aplanados
        """
        flattened_data = []
        
        for handle, posts in results.items():
            for post in posts:
                flat_post = {
                    'user_handle': handle,
                    'post_uri': post['uri'],
                    'post_cid': post['cid'],
                    'author_did': post['author']['did'],
                    'author_handle': post['author']['handle'],
                    'author_display_name': post['author']['display_name'],
                    'text': post['text'],
                    'created_at': post['created_at'],
                    'likes': post['likes'],
                    'reposts': post['reposts'],
                    'replies': post['replies']
                }
                
                # Añadir imágenes si existen
                if 'images' in post:
                    flat_post['images'] = ', '.join(post['images'])
                
                flattened_data.append(flat_post)
                
        return flattened_data
        
    def save_results_to_csv(self, results: Dict[str, List[Dict[str, Any]]], filename: str = None) -> Optional[str]:
        """
        Guarda los resultados en un archivo CSV utilizando Polars.
        
        Args:
            results: Diccionario con los resultados
            filename: Nombre del archivo (opcional)
            
        Returns:
            str: Ruta del archivo guardado, o None si hubo un error
        """
        if not POLARS_AVAILABLE:
            print("❌ No se puede exportar a CSV: polars no está instalado.")
            return None
            
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bluesky_posts_{timestamp}.csv"
            
        try:
            # Convertir los datos a una estructura plana
            flattened_data = self._flatten_results(results)
            
            # Crear DataFrame y guardar como CSV con Polars
            df = pl.DataFrame(flattened_data)
            df.write_csv(filename)
            
            print(f"✅ Resultados guardados en {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error al exportar a CSV: {str(e)}")
            return None
            
    def save_results_to_parquet(self, results: Dict[str, List[Dict[str, Any]]], filename: str = None) -> Optional[str]:
        """
        Guarda los resultados en un archivo Parquet utilizando Polars.
        
        Args:
            results: Diccionario con los resultados
            filename: Nombre del archivo (opcional)
            
        Returns:
            str: Ruta del archivo guardado, o None si hubo un error
        """
        if not POLARS_AVAILABLE:
            print("❌ No se puede exportar a Parquet: polars no está instalado.")
            return None
            
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bluesky_posts_{timestamp}.parquet"
            
        try:
            # Convertir los datos a una estructura plana
            flattened_data = self._flatten_results(results)
            
            # Crear DataFrame y guardar como Parquet con Polars
            df = pl.DataFrame(flattened_data)
            df.write_parquet(filename)
            
            print(f"✅ Resultados guardados en {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error al exportar a Parquet: {str(e)}")
            return None
            
    def export_results(self, results: Dict[str, List[Dict[str, Any]]], format: str = 'json', filename: str = None) -> Optional[str]:
        """
        Exporta los resultados en el formato especificado.
        
        Args:
            results: Diccionario con los resultados
            format: Formato de exportación ('json', 'csv' o 'parquet')
            filename: Nombre del archivo (opcional)
            
        Returns:
            str: Ruta del archivo guardado, o None si hubo un error
        """
        format = format.lower()
        
        if format == 'json':
            return self.save_results_to_json(results, filename)
        elif format == 'csv':
            return self.save_results_to_csv(results, filename)
        elif format == 'parquet':
            return self.save_results_to_parquet(results, filename)
        else:
            print(f"❌ Formato no soportado: {format}")
            print("Formatos disponibles: json, csv, parquet")
            return None

def main():
    """Función principal del script."""
    # Acceder a la variable global
    global POLARS_AVAILABLE
    
    parser = argparse.ArgumentParser(description='Obtiene posts de usuarios de Bluesky')
    parser.add_argument('-u', '--username', help='Nombre de usuario o correo electrónico para autenticación')
    parser.add_argument('-p', '--password', help='Contraseña para autenticación')
    parser.add_argument('-f', '--file', help='Archivo con lista de usuarios (uno por línea)')
    parser.add_argument('-l', '--list', nargs='+', help='Lista de usuarios separados por espacios')
    parser.add_argument('-n', '--limit', type=int, default=20, help='Número máximo de posts por usuario')
    parser.add_argument('-o', '--output', help='Nombre del archivo de salida')
    parser.add_argument('-x', '--format', choices=['json', 'csv', 'parquet'], default='json',
                        help='Formato de exportación: json, csv o parquet')
    
    args = parser.parse_args()
    
    # Verificar credenciales
    if not args.username or not args.password:
        # Intentar leer de archivo de credenciales
        credentials_file = 'credentials_example.txt'
        if os.path.exists(credentials_file):
            try:
                with open(credentials_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        args.username = lines[0].strip()
                        args.password = lines[1].strip()
                        print(f"✅ Credenciales cargadas desde {credentials_file}")
                    else:
                        raise ValueError("El archivo de credenciales no tiene el formato correcto")
            except Exception as e:
                print(f"❌ Error al leer credenciales: {str(e)}")
                print("⚠️ Se requieren credenciales para autenticación.")
                args.username = input("Usuario o correo electrónico: ")
                args.password = input("Contraseña: ")
        else:
            print("⚠️ Se requieren credenciales para autenticación.")
            args.username = input("Usuario o correo electrónico: ")
            args.password = input("Contraseña: ")
    
    # Verificar lista de usuarios
    handles = []
    
    # Comprobar si se especificó un archivo en la línea de comandos
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                handles = [line.strip() for line in f if line.strip()]
            print(f"✅ Usuarios cargados desde {args.file}")
        except Exception as e:
            print(f"❌ Error al leer el archivo: {str(e)}")
    # Si no se especificó archivo, intentar leer de usuarios.txt
    elif os.path.exists('usuarios.txt'):
        try:
            with open('usuarios.txt', 'r', encoding='utf-8') as f:
                handles = [line.strip() for line in f if line.strip()]
            print(f"✅ Usuarios cargados automáticamente desde usuarios.txt")
        except Exception as e:
            print(f"❌ Error al leer usuarios.txt: {str(e)}")
    
    # Añadir usuarios de la línea de comandos si se especificaron
    if args.list:
        handles.extend(args.list)
    
    # Si todavía no hay usuarios, pedir al usuario
    if not handles:
        print("⚠️ No se ha especificado ninguna lista de usuarios.")
        user_input = input("Ingresa usuarios separados por comas: ")
        handles = [h.strip() for h in user_input.split(',') if h.strip()]
    
    # Iniciar el proceso
    fetcher = BlueskyPostsFetcher(args.username, args.password)
    results = fetcher.get_posts_from_list(handles, args.limit)
    
    # Guardar resultados
    if results:
        # Verificar si el formato seleccionado necesita polars y no está disponible
        if args.format in ['csv', 'parquet'] and not POLARS_AVAILABLE:
            print(f"⚠️ El formato {args.format} requiere polars pero no se pudo instalar automáticamente.")
            print("Instale dependencias con: uv pip install -r requirements.txt")
            format_choice = input("Instalar ahora las dependencias (S) o usar JSON por ahora (J)? [S/J]: ").strip().upper()
            if format_choice == 'S':
                try:
                    print("Instalando polars con uv...")
                    subprocess.check_call(["uv", "pip", "install", "-r", "requirements.txt"])
                    print("✅ Polars instalado correctamente")
                    try:
                        import polars as pl
                        POLARS_AVAILABLE = True
                    except ImportError:
                        print("❌ Error al importar polars después de la instalación.")
                        args.format = 'json'
                except Exception as e:
                    print(f"❌ Error al instalar polars: {str(e)}")
                    print("Utilizando formato JSON por defecto.")
                    args.format = 'json'
            else:
                print("Utilizando formato JSON por defecto.")
                args.format = 'json'
        
        # Si no se especificó un archivo de salida, usar nombre predeterminado
        if not args.output:
            default_filename = f"bluesky_posts_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{args.format}"
            args.output = default_filename
        
        # Añadir extensión si no tiene
        if not args.output.endswith(f'.{args.format}'):
            args.output = f"{args.output}.{args.format}"
        
        # Exportar en el formato seleccionado
        fetcher.export_results(results, args.format, args.output)
    else:
        print("❌ No se encontraron resultados.")

if __name__ == "__main__":
    main()
