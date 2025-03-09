#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bluesky Posts Fetcher

Este script permite obtener los posts recientes de una lista de usuarios de Bluesky.
Utiliza la biblioteca atproto para interactuar con la API de AT Protocol.
"""

import os
import json
import re
import argparse
import datetime
import time
from typing import List, Dict, Any, Optional
from atproto import Client
import atproto_client.exceptions

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
            
    def get_web_url_from_uri(self, uri: str, author_handle: str) -> str:
        """
        Convierte un URI de AT Protocol a una URL web visible en el navegador.
        
        Args:
            uri: URI del post en formato at://did:plc:xyz/app.bsky.feed.post/abc123
            author_handle: Handle del autor del post
            
        Returns:
            str: URL web en formato https://bsky.app/profile/handle/post/abc123
        """
        try:
            # Extraer el ID del post del URI (la última parte del path)
            post_id = uri.split('/')[-1]
            
            # Crear la URL web de Bluesky
            web_url = f"https://bsky.app/profile/{author_handle}/post/{post_id}"
            return web_url
        except:
            # En caso de error, devolver None
            return None
    
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
            
            # Obtener los posts del usuario con paginación para respetar el límite de 100 de la API
            posts = []
            cursor = None
            posts_collected = 0
            original_limit = limit
            
            # Calcular número aproximado de llamadas necesarias
            api_calls_needed = max(1, (original_limit + 99) // 100)  # Redondeo hacia arriba
            
            # Iterar hasta alcanzar el límite o hasta que no haya más resultados
            for call_num in range(api_calls_needed):
                # Calcular el límite para esta llamada (máximo 100)
                current_call_limit = min(100, original_limit - posts_collected)
                
                if current_call_limit <= 0:
                    break
                
                # Parámetros para obtener el feed
                feed_params = {
                    "actor": handle,
                    "limit": current_call_limit
                }
                
                # Añadir cursor si no es la primera llamada
                if cursor:
                    feed_params["cursor"] = cursor
                
                # Obtener los posts
                try:
                    author_feed = self.client.get_author_feed(**feed_params)
                    
                    # Guardar el cursor para la siguiente página si existe
                    cursor = getattr(author_feed, 'cursor', None)
                    
                    # Si no hay resultados o no hay cursor, terminar el bucle
                    if not hasattr(author_feed, 'feed') or len(author_feed.feed) == 0:
                        break
                    
                    # Procesar los posts de esta página
                    for feed_view in author_feed.feed:
                        try:
                            post = feed_view.post
                            posts_collected += 1
                            
                            # Extraer información relevante
                            post_data = {
                                'uri': post.uri,
                                'cid': post.cid,
                                'web_url': self.get_web_url_from_uri(post.uri, post.author.handle),
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
                            if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images') and post.record.embed.images is not None:
                                # Extraer URLs de las imágenes usando el mismo método que search_posts
                                image_urls = []
                                for img in post.record.embed.images:
                                    if hasattr(img, 'image'):
                                        img_obj = img.image
                                        if hasattr(img_obj, 'cid') and img_obj.cid:
                                            # Convertir el objeto CID a string
                                            cid_str = str(img_obj.cid)
                                            author_did = post.author.did
                                            # Construir URL usando el CID válido como string
                                            image_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={cid_str}"
                                            image_urls.append(image_url)
                                
                                if image_urls:
                                    post_data['images'] = image_urls
                            
                            # Determinar el tipo de post
                            # Verificar primero si es un reply basado en la existencia de un atributo reply con valor no nulo
                            if hasattr(post.record, 'reply') and post.record.reply is not None:
                                post_data['post_type'] = 'reply'
                            else:
                                # Para los posts que no son replies, verificar si son reposts
                                # Primero ver si el author DID coincide con el DID del usuario solicitado
                                # Si el post aparece en la timeline de un usuario pero no fue creado por ese usuario, es un repost
                                try:
                                    # Obtener el DID del usuario cuya timeline estamos viendo
                                    user_profile = None
                                    if hasattr(self.client, '_me') and self.client._me:
                                        user_did = self.client._me.did
                                    else:
                                        # Si no tenemos el DID en la sesión, intentar obtenerlo de la API
                                        user_profile = self.client.app.bsky.actor.get_profile({'actor': handle})
                                        user_did = user_profile.did
                                    
                                    # Si el DID del usuario y el autor del post son diferentes, es un repost
                                    if post.author.did != user_did:
                                        post_data['post_type'] = 'repost'
                                    else:
                                        post_data['post_type'] = 'original'
                                except Exception:
                                    # Si hay algún error al comparar DIDs, usar método alternativo
                                    # Verificar si hay indicadores de repost como en la versión anterior
                                    if hasattr(post, 'reason') and post.reason is not None:
                                        if hasattr(post.reason, 'py_type') and 'repost' in str(post.reason.py_type).lower():
                                            post_data['post_type'] = 'repost'
                                        else:
                                            post_data['post_type'] = 'original'
                                    else:
                                        post_data['post_type'] = 'original'
                            
                            # Extraer URLs del contenido del post (dos métodos)
                            urls = []
                            
                            # Extraer menciones de usuarios
                            mentions = []
                            
                            # Extraer URLs y menciones de facets (formato estructurado de Bluesky)
                            if hasattr(post.record, 'facets') and post.record.facets:
                                for facet in post.record.facets:
                                    if hasattr(facet, 'features'):
                                        for feature in facet.features:
                                            # Identificar el tipo de feature según su py_type
                                            if hasattr(feature, 'py_type'):
                                                # Extraer links
                                                if feature.py_type == 'app.bsky.richtext.facet#link' and hasattr(feature, 'uri'):
                                                    urls.append(feature.uri)
                                                # Extraer menciones
                                                elif feature.py_type == 'app.bsky.richtext.facet#mention' and hasattr(feature, 'did'):
                                                    # Intentar obtener el handle si está disponible
                                                    if hasattr(feature, 'handle'):
                                                        mentions.append(feature.handle)
                                                    else:
                                                        mentions.append(feature.did)
                            
                            # 2. Como respaldo, también buscar URLs con regex en el texto
                            import re
                            url_pattern = r'https?://[\w\-\.]+(?:/[\w\-\./%?&=+#]*)?'
                            if post.record.text:
                                regex_urls = re.findall(url_pattern, post.record.text)
                                # Añadir URLs que no se hayan encontrado en facets
                                for url in regex_urls:
                                    if url not in urls:
                                        urls.append(url)
                            
                            # Almacenar URLs si se encontraron
                            if urls:
                                post_data['urls'] = urls
                                
                            # Almacenar menciones si se encontraron
                            if mentions:
                                post_data['mentions'] = mentions
                            
                            posts.append(post_data)
                        except Exception as inner_e:
                            # Si hay un error procesando un post individual, continuar con el siguiente
                            print(f"⚠️ Error procesando un post de @{handle}: {str(inner_e)}")
                            continue
                except Exception as e:
                    print(f"❌ Error al obtener posts (página {call_num + 1}) de @{handle}: {str(e)}")
                    break
            
            print(f"✅ Obtenidos {len(posts)} posts de @{handle}")
            return posts
        
        except Exception as e:
            print(f"❌ Error al obtener posts de @{handle}: {str(e)}")
            return []
    
    def parse_bluesky_list_url(self, url: str) -> Dict[str, str]:
        """
        Extrae el handle del usuario y el ID de la lista de una URL de lista de Bluesky.
        
        Args:
            url: URL de la lista de Bluesky. Formatos admitidos:
                - https://bsky.app/profile/usuario.bsky.social/lists/123abc
                - at://did:plc:xxx/app.bsky.graph.list/123abc
                - did:plc:xxx/app.bsky.graph.list/123abc
            
        Returns:
            Dict: Diccionario con 'handle' e 'id' de la lista, o None si la URL no es válida
        """
        import re
        
        # 1. Verificar si es una URL de bsky.app (formato de navegador)
        browser_pattern = r'bsky\.app/profile/([^/]+)/lists/([^/]+)'
        browser_match = re.search(browser_pattern, url)
        if browser_match:
            return {
                'handle': browser_match.group(1).strip().strip('"').strip("'"),
                'list_id': browser_match.group(2).strip().strip('"').strip("'")
            }
        
        # 2. Verificar si es una URI AT Protocol completa (at://did:plc:...)
        at_uri_pattern = r'at://([^/]+)/app\.bsky\.graph\.list/([^/]+)'
        at_uri_match = re.search(at_uri_pattern, url)
        if at_uri_match:
            return {
                'handle': at_uri_match.group(1).strip().strip('"').strip("'"),  # Este será un DID
                'list_id': at_uri_match.group(2).strip().strip('"').strip("'")
            }
        
        # 3. Verificar si es una URI parcial (did:plc:...)
        did_uri_pattern = r'(did:[^/]+)/app\.bsky\.graph\.list/([^/]+)'
        did_uri_match = re.search(did_uri_pattern, url)
        if did_uri_match:
            return {
                'handle': did_uri_match.group(1).strip().strip('"').strip("'"),  # Este será un DID
                'list_id': did_uri_match.group(2).strip().strip('"').strip("'")
            }
            
        # Si ninguno de los patrones coincide, la URL no es válida
        print(f"❌ Formato de URL de lista no reconocido: {url}")
        print("Formatos admitidos:")
        print(" - https://bsky.app/profile/usuario.bsky.social/lists/123abc")
        print(" - at://did:plc:xxx/app.bsky.graph.list/123abc")
        print(" - did:plc:xxx/app.bsky.graph.list/123abc")
        return None
    
    def get_posts_from_bluesky_list(self, handle: str, list_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene posts directamente de una lista de Bluesky.
        
        Args:
            handle: Handle del propietario de la lista
            list_id: ID de la lista
            limit: Número máximo de posts a obtener (con paginación automática si es mayor que 100)
            
        Returns:
            List[Dict]: Lista de posts obtenidos de la lista
        """
        try:
            # Verificar si el handle ya es un DID (identificador descentralizado)
            if handle.startswith('did:'):
                profile_did = handle
            else:
                # Obtener el DID del handle
                profile = self.client.get_profile(actor=handle)
                profile_did = profile.did
            
            # Aplicar una limpieza completa con el método especializado
            list_id = self._sanitize_uri_component(list_id)
            profile_did = self._sanitize_uri_component(profile_did)
            
            # Construir el URI de la lista en el formato correcto para la API de AT Protocol
            # El formato debe ser: at://did:plc:xxx/app.bsky.graph.list/listname sin comillas
            list_uri = f"at://{profile_did}/app.bsky.graph.list/{list_id}"
            
            # Validar que no quedan comillas o espacios en el URI final
            if '"' in list_uri or "'" in list_uri:
                print('\n⚠️ Detectadas comillas en el URI. Limpiando...')
                list_uri = re.sub(r'["\']+', '', list_uri)
            # Usar comillas simples para el print para evitar problemas con comillas extras
            print('Obteniendo lista:', list_uri)
            
            # Obtener información básica de la lista
            try:
                # Asegurarse de que el parámetro de la API no tenga comillas extra
                response = self.client.app.bsky.graph.get_list({"list": list_uri})
            except Exception as e:
                print('Error al obtener la lista con URI:', list_uri)
                print('Detalle del error:', e.content.message if hasattr(e, 'content') and hasattr(e.content, 'message') else str(e))
                
                # Verificar si hay información de rate limiting en los headers
                self._check_rate_limit_info(e)
                
                # Intento con el URI sin la última comilla si quedó alguna
                if list_uri.endswith('"'):
                    list_uri = list_uri[:-1]
                    print('Intentando sin comilla final:', list_uri)
                    try:
                        response = self.client.app.bsky.graph.get_list({"list": list_uri})
                        return self._process_list_response(response, list_id, limit)
                    except Exception:
                        pass
                
                # Asegurar que los componentes están completamente limpios
                clean_profile_did = self._sanitize_uri_component(profile_did)
                clean_list_id = self._sanitize_uri_component(list_id)
                
                # Intento con el URI correcto para la API (sin el prefijo at://)
                alt_list_uri = f"{clean_profile_did}/app.bsky.graph.list/{clean_list_id}"
                print('Intentando formato alternativo:', alt_list_uri)
                
                try:
                    response = self.client.app.bsky.graph.get_list({"list": alt_list_uri})
                except Exception as e2:
                    self._check_rate_limit_info(e2)
                    
                    # Intento una última alternativa eliminando cualquier caracter no alfanumérico del list_id
                    final_list_id = re.sub(r'[^a-zA-Z0-9]+', '', list_id)
                    if final_list_id != clean_list_id:
                        try:
                            final_uri = f"{clean_profile_did}/app.bsky.graph.list/{final_list_id}"
                            print('Intentando URI con solo caracteres alfanuméricos:', final_uri)
                            response = self.client.app.bsky.graph.get_list({"list": final_uri})
                            return self._process_list_response(response, final_list_id, limit)
                        except Exception:
                            pass
                    
                    # Si todos los intentos fallan, mostrar información de depuración
                    print('\n⛔ Todos los formatos de URI fallaron. Información para depuración:')
                    print(f"  - DID del perfil: '{profile_did}'")
                    print(f"  - ID de la lista (original): '{list_id}'")
                    print(f"  - ID de la lista (limpio): '{clean_list_id}'")
                    print(f"  - URI completo: '{list_uri}'")
                    print(f"  - URI alternativo: '{alt_list_uri}'")
                    print("\nPor favor, comprueba que el ID de la lista es correcto en la URL de origen.")
                    raise
            
            list_name = "Lista"
            if hasattr(response, 'list') and hasattr(response.list, 'name'):
                list_name = response.list.name
                print(f"Lista encontrada: {list_name}")
                
            # Implementar paginación para obtener más de 100 posts (límite de la API)
            original_limit = limit
            posts = []
            posts_collected = 0
            cursor = None
            
            # Calcular el número aproximado de llamadas a la API necesarias
            api_call_limit = min(100, limit)  # La API permite máximo 100 posts por llamada
            api_calls_needed = (limit + api_call_limit - 1) // api_call_limit  # Redondeo hacia arriba
            
            if api_calls_needed > 1:
                print(f"📢 Solicitando {original_limit} posts de la lista (se harán aproximadamente {api_calls_needed} llamadas a la API)")
            
            # Bucle de paginación
            for call_num in range(1, api_calls_needed + 1):
                # Calcular cuántos posts quedan por obtener
                remaining_limit = min(api_call_limit, limit - posts_collected)
                
                if api_calls_needed > 1:
                    print(f"🔍 Realizando llamada {call_num} de ~{api_calls_needed} (obteniendo {remaining_limit} posts)")
                
                # Preparar parámetros para la llamada a la API
                params = {"list": list_uri, "limit": remaining_limit}
                if cursor:
                    params["cursor"] = cursor
                
                # Realizar la llamada a la API
                list_feed = self.client.app.bsky.feed.get_list_feed(params)
                
                # Obtener el cursor para la siguiente página
                cursor = getattr(list_feed, 'cursor', None)
                
                page_posts = []
                # Procesar los posts de esta página
                if hasattr(list_feed, 'feed'):
                    for feed_view in list_feed.feed:
                        post = feed_view.post
                        
                        # Extraer información relevante (mismo formato que get_user_posts)
                        post_data = {
                            'uri': post.uri,
                            'cid': post.cid,
                            'web_url': self.get_web_url_from_uri(post.uri, post.author.handle),
                            'author': {
                                'did': post.author.did,
                                'handle': post.author.handle,
                                'display_name': getattr(post.author, 'display_name', post.author.handle)
                            },
                            'text': post.record.text,
                            'created_at': post.record.created_at,
                            'likes': getattr(post, 'like_count', 0),
                            'reposts': getattr(post, 'repost_count', 0),
                            'replies': getattr(post, 'reply_count', 0),
                            'urls': [],
                            'mentions': []
                        }
                        
                        # Procesar imágenes exactamente igual que en search_posts
                        if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images') and post.record.embed.images is not None:
                            # Extraer URLs de las imágenes
                            image_urls = []
                            
                            for img in post.record.embed.images:
                                if hasattr(img, 'image'):
                                    # Intentar obtener CID válido
                                    img_obj = img.image
                                    cid = None
                                    
                                    # Extraer CID como string para la URL
                                    if hasattr(img_obj, 'cid') and img_obj.cid:
                                        # Convertir el objeto CID a string
                                        cid_str = str(img_obj.cid)
                                        author_did = post.author.did
                                        # Construir URL usando el CID válido como string
                                        image_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={cid_str}"
                                        image_urls.append(image_url)
                            
                            # Solo añadir el campo 'images' si hay URLs válidas
                            if image_urls:
                                post_data['images'] = image_urls
                            
                        # Extraer menciones de usuarios y URLs exactamente igual que en search_posts
                        urls = []
                        mentions = []
                        
                        # Extraer URLs y menciones de facets (formato estructurado de Bluesky)
                        if hasattr(post.record, 'facets') and post.record.facets:
                            for facet in post.record.facets:
                                if hasattr(facet, 'features'):
                                    for feature in facet.features:
                                        # Identificar el tipo de feature según su py_type
                                        if hasattr(feature, 'py_type'):
                                            # Extraer links
                                            if feature.py_type == 'app.bsky.richtext.facet#link' and hasattr(feature, 'uri'):
                                                urls.append(feature.uri)
                                            # Extraer menciones
                                            elif feature.py_type == 'app.bsky.richtext.facet#mention' and hasattr(feature, 'did'):
                                                # Intentar obtener el handle si está disponible
                                                if hasattr(feature, 'handle'):
                                                    mentions.append(feature.handle)
                                                else:
                                                    mentions.append(feature.did)
                        
                        # 2. Como respaldo, también buscar URLs con regex en el texto
                        import re
                        url_pattern = r'https?://[\w\-\.]+(?:/[\w\-\./%?&=+#]*)?'
                        if post.record.text:
                            regex_urls = re.findall(url_pattern, post.record.text)
                            # Añadir URLs que no se hayan encontrado en facets
                            for url in regex_urls:
                                if url not in urls:
                                    urls.append(url)
                        
                        # Almacenar URLs si se encontraron
                        if urls:
                            post_data['urls'] = urls
                            
                        # Almacenar menciones si se encontraron
                        if mentions:
                            post_data['mentions'] = mentions
                        
                        page_posts.append(post_data)
                
                # Añadir los posts de esta página a la lista completa
                posts.extend(page_posts)
                posts_collected += len(page_posts)
                
                # Mostrar progreso
                if api_calls_needed > 1:
                    print(f"ℹ️ Obtenidos {posts_collected} de {original_limit} posts solicitados")
                
                # Si no hay cursor o ya hemos alcanzado el límite, terminar
                if not cursor or posts_collected >= original_limit:
                    break
                    time.sleep(0.5)  # Pausa de medio segundo entre llamadas
            
            if posts:
                # Obtener el rango de fechas para mostrar
                if len(posts) > 1:
                    dates = [post['created_at'] for post in posts]
                    oldest = min(dates)
                    newest = max(dates)
                    print(f"📅 Rango de fechas: {oldest} a {newest}")
            
            print(f"✅ Obtenidos {len(posts)} posts de la lista '{list_name}' de @{handle}")
            return posts
            
        except Exception as e:
            print(f"❌ Error al obtener posts de la lista: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_posts_from_bluesky_list_url(self, list_url: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtiene posts directamente de una lista de Bluesky usando la URL de la lista.
        
        Args:
            list_url: URL de la lista de Bluesky (ej: https://bsky.app/profile/usuario.bsky.social/lists/123abc)
            limit: Número máximo de posts a obtener
            
        Returns:
            Dict: Diccionario con los posts organizados por autor
        """
        # Eliminar todo tipo de caracteres no deseados que puedan estar en la URL
        # usando el método especializado de limpieza
        list_url = self._sanitize_uri_component(list_url)
        print('URL de lista procesada:', list_url)
        
        list_info = self.parse_bluesky_list_url(list_url)
        if not list_info:
            print('❌ URL de lista no válida:', list_url)
            print("Formato esperado: https://bsky.app/profile/usuario.bsky.social/lists/123abc")
            return {}
        
        # Limpiar el handle y list_id de cualquier caracter no deseado con el método especializado
        handle = self._sanitize_uri_component(list_info['handle'])
        list_id = self._sanitize_uri_component(list_info['list_id'])
        
        print('Handle limpio:', handle)
        print('ID de lista limpio:', list_id)
        
        # Obtener posts directamente de la lista
        list_posts = self.get_posts_from_bluesky_list(handle, list_id, limit)
        if not list_posts:
            return {}
        
        # Organizar los posts por autor
        results = {}
        for post in list_posts:
            author_handle = post['author']['handle']
            if author_handle not in results:
                results[author_handle] = []
            results[author_handle].append(post)
            
        return results
    
    def get_posts_from_users(self, handles: List[str], limit_per_user: int = 20) -> Dict[str, List[Dict[str, Any]]]:
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
        # Crear directorio 'data' si no existe
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bluesky_posts_{timestamp}.json"
        
        # Añadir directorio data al path si no lo tiene ya
        if not filename.startswith(data_dir):
            filename = os.path.join(data_dir, os.path.basename(filename))
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Resultados guardados en {filename}")
        return filename
        
    def _sanitize_uri_component(self, component):
        """
        Limpia un componente de URI para asegurar que no contiene comillas ni caracteres conflictivos.
        
        Args:
            component: Texto a limpiar
            
        Returns:
            str: Componente limpio sin comillas ni espacios
        """
        if component is None:
            return ""
            
        # Primer paso: eliminar espacios y comillas del inicio y final
        cleaned = component.strip().strip('"').strip("'").strip()
        
        # Segundo paso: eliminar cualquier comilla restante usando regex
        cleaned = re.sub(r'["\']+', '', cleaned)
        
        # Tercer paso: eliminar cualquier espacio en blanco
        cleaned = re.sub(r'\s+', '', cleaned)
        
        return cleaned
        
    def _check_rate_limit_info(self, exception):
        """
        Extrae y muestra información de rate limiting de los headers de la API.
        
        Args:
            exception: Excepción de la API que puede contener headers con información de rate limiting
        """
        if not hasattr(exception, 'headers'):
            return
            
        rate_limit = {}
        headers = exception.headers
        
        # Extraer información de rate limiting de los headers
        if 'ratelimit-limit' in headers:
            rate_limit['limit'] = headers['ratelimit-limit']
        if 'ratelimit-remaining' in headers:
            rate_limit['remaining'] = headers['ratelimit-remaining']
        if 'ratelimit-reset' in headers:
            rate_limit['reset'] = headers['ratelimit-reset']
        if 'ratelimit-policy' in headers:
            rate_limit['policy'] = headers['ratelimit-policy']
        
        # Mostrar información al usuario si hay datos de rate limiting
        if rate_limit:
            print('\n⚠️ Información de límites de la API (Rate Limiting):')
            print(f"  - Límite: {rate_limit.get('limit', 'N/A')} solicitudes")
            print(f"  - Restante: {rate_limit.get('remaining', 'N/A')} solicitudes")
            print(f"  - Reinicio: {rate_limit.get('reset', 'N/A')} (timestamp)")
            print(f"  - Política: {rate_limit.get('policy', 'N/A')}")
            
            # Si estamos cerca del límite, sugerir esperar
            try:
                remaining = int(rate_limit.get('remaining', 0))
                if remaining < 100:
                    print("\n⚠️ Estás cerca del límite de rate limiting.")
                    print("   Considera esperar unos minutos antes de realizar más solicitudes.")
            except (ValueError, TypeError):
                pass
        
    def _flatten_results(self, results: Dict[str, List[Dict[str, Any]]], sort_by_date: bool = True) -> List[Dict[str, Any]]:
        """
        Convierte los resultados anidados a una estructura plana para exportación a CSV/Parquet.
        
        Args:
            results: Diccionario con los resultados
            sort_by_date: Si es True, ordena los posts por fecha de creación (más recientes primero)
            
        Returns:
            List[Dict]: Lista de posts aplanados
        """
        flattened_data = []
        
        # Recopilamos todos los posts en una lista plana
        for handle, posts in results.items():
            for post in posts:
                flat_post = {
                    'user_handle': handle,
                    'post_uri': post['uri'],
                    'post_web_url': post.get('web_url', ''),  # Incluir la URL web para abrir en navegador
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
                if 'images' in post and post['images']:
                    # Usar formato JSON array para mantener múltiples imágenes
                    import json
                    flat_post['images'] = json.dumps(post['images'])
                else:
                    # Establecer como null cuando no hay imágenes
                    flat_post['images'] = None
                
                # Añadir URLs si existen
                if 'urls' in post and post['urls']:
                    # Usar formato JSON array para mantener múltiples URLs
                    import json
                    flat_post['urls'] = json.dumps(post['urls'])
                else:
                    # Establecer como null cuando no hay URLs
                    flat_post['urls'] = None
                
                # Añadir menciones si existen
                if 'mentions' in post and post['mentions']:
                    # Usar formato JSON array para mantener múltiples menciones
                    import json
                    flat_post['mentions'] = json.dumps(post['mentions'])
                else:
                    # Establecer como null cuando no hay menciones
                    flat_post['mentions'] = None
                
                # Añadir tipo de post
                flat_post['post_type'] = post.get('post_type', 'original')  # 'original' como valor por defecto
                
                flattened_data.append(flat_post)
        
        # Ordenar por fecha de creación (más recientes primero) si se solicita
        if sort_by_date and flattened_data:
            try:
                flattened_data.sort(key=lambda x: x['created_at'], reverse=True)
                print("📅 Posts ordenados cronológicamente (más recientes primero)")
            except Exception as e:
                print(f"⚠️ No se pudieron ordenar los posts por fecha: {str(e)}")
                
        return flattened_data
        
    def save_results_to_csv(self, results: Dict[str, List[Dict[str, Any]]], filename: str = None, sort_by_date: bool = True) -> Optional[str]:
        """
        Guarda los resultados en un archivo CSV utilizando Polars.
        
        Args:
            results: Diccionario con los resultados
            filename: Nombre del archivo (opcional)
            sort_by_date: Si es True, ordena los posts por fecha de creación (más recientes primero)
            
        Returns:
            str: Ruta del archivo guardado, o None si hubo un error
        """
        if not POLARS_AVAILABLE:
            print("❌ No se puede exportar a CSV: polars no está instalado.")
            return None
        
        # Crear directorio 'data' si no existe
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
            
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bluesky_posts_{timestamp}.csv"
        
        # Añadir directorio data al path si no lo tiene ya
        if not filename.startswith(data_dir):
            filename = os.path.join(data_dir, os.path.basename(filename))
            
        try:
            # Convertir los datos a una estructura plana
            flattened_data = self._flatten_results(results, sort_by_date=sort_by_date)
            
            # Crear DataFrame y ordenar columnas según el orden especificado
            df = pl.DataFrame(flattened_data)
            
            # Definir el orden de las columnas deseado
            column_order = [
                'author_handle',
                'author_display_name',
                'created_at',
                'post_web_url',
                'text',
                'likes',
                'reposts',
                'replies',
                'images',
                'urls',
                'mentions',
                'post_type',
                'user_handle',
                'post_cid',
                'author_did',
                'post_uri'
            ]
            
            # Asegurarse de que todas las columnas existan (algunas podrían faltar como 'images')
            existing_columns = set(df.columns)
            ordered_columns = [col for col in column_order if col in existing_columns]
            remaining_columns = [col for col in existing_columns if col not in column_order]
            
            # Reordenar las columnas y escribir el CSV
            df = df.select(ordered_columns + remaining_columns)
            df.write_csv(filename)
            
            print(f"✅ Resultados guardados en {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error al exportar a CSV: {str(e)}")
            return None
            
    def save_results_to_parquet(self, results: Dict[str, List[Dict[str, Any]]], filename: str = None, sort_by_date: bool = True) -> Optional[str]:
        """
        Guarda los resultados en un archivo Parquet utilizando Polars.
        
        Args:
            results: Diccionario con los resultados
            filename: Nombre del archivo (opcional)
            sort_by_date: Si es True, ordena los posts por fecha de creación (más recientes primero)
            
        Returns:
            str: Ruta del archivo guardado, o None si hubo un error
        """
        if not POLARS_AVAILABLE:
            print("❌ No se puede exportar a Parquet: polars no está instalado.")
            return None
        
        # Crear directorio 'data' si no existe
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
            
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bluesky_posts_{timestamp}.parquet"
        
        # Añadir directorio data al path si no lo tiene ya
        if not filename.startswith(data_dir):
            filename = os.path.join(data_dir, os.path.basename(filename))
            
        try:
            # Convertir los datos a una estructura plana
            flattened_data = self._flatten_results(results, sort_by_date=sort_by_date)
            
            # Crear DataFrame y ordenar columnas según el orden especificado
            df = pl.DataFrame(flattened_data)
            
            # Definir el orden de las columnas deseado
            column_order = [
                'author_handle',
                'author_display_name',
                'created_at',
                'post_web_url',
                'text',
                'likes',
                'reposts',
                'replies',
                'images',
                'urls',
                'mentions',
                'post_type',
                'user_handle',
                'post_cid',
                'author_did',
                'post_uri'
            ]
            
            # Asegurarse de que todas las columnas existan (algunas podrían faltar como 'images')
            existing_columns = set(df.columns)
            ordered_columns = [col for col in column_order if col in existing_columns]
            remaining_columns = [col for col in existing_columns if col not in column_order]
            
            # Reordenar las columnas y escribir el Parquet
            df = df.select(ordered_columns + remaining_columns)
            df.write_parquet(filename)
            
            print(f"✅ Resultados guardados en {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error al exportar a Parquet: {str(e)}")
            return None
            
    def search_posts(self, query: str, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """
        Busca posts en Bluesky basado en múltiples parámetros de búsqueda.
        Soporta paginación para obtener más de 100 resultados mediante múltiples llamadas a la API.
        
        Args:
            query: Texto a buscar
            limit: Número máximo de resultados deseados (se harán múltiples llamadas a la API si es necesario)
            **kwargs: Parámetros adicionales de búsqueda:                
                - from_user: Posts de un usuario específico (equivalent to from:handle)
                - mention: Posts que mencionan a un usuario específico (equivalent to mentions:handle)
                - language: Idioma de los posts (equivalent to lang:code)
                - since: Fecha de inicio (formato YYYY-MM-DD)
                - until: Fecha de fin (formato YYYY-MM-DD)
                - domain: Dominio específico de URLs en posts (equivalent to domain:example.com)
                - sort: Orden de los resultados ('latest' para más recientes o 'top' para relevancia/popularidad)
            
        Returns:
            List[Dict]: Lista de posts encontrados
        """
        try:
            original_limit = limit
            posts = []
            api_calls_needed = (limit + 99) // 100  # Redondeo hacia arriba para calcular el número de llamadas necesarias
            posts_collected = 0
            cursor = None
            
            # Construir la consulta con los parámetros
            search_query = query
            
            # Añadir filtros a la consulta según los parámetros proporcionados
            if 'from_user' in kwargs and kwargs['from_user']:
                search_query = f"{search_query} from:{kwargs['from_user']}"
                
            if 'mention' in kwargs and kwargs['mention']:
                search_query = f"{search_query} mentions:{kwargs['mention']}"
                
            if 'language' in kwargs and kwargs['language']:
                search_query = f"{search_query} lang:{kwargs['language']}"
                
            if 'since' in kwargs and kwargs['since']:
                search_query = f"{search_query} since:{kwargs['since']}"
                
            if 'until' in kwargs and kwargs['until']:
                search_query = f"{search_query} until:{kwargs['until']}"
                
            if 'domain' in kwargs and kwargs['domain']:
                search_query = f"{search_query} domain:{kwargs['domain']}"
            
            print(f"📝 Consulta de búsqueda: {search_query}")
            if original_limit > 100:
                print(f"📢 Solicitando {original_limit} posts (se harán aproximadamente {api_calls_needed} llamadas a la API)")
            
            # Realizar múltiples búsquedas hasta alcanzar el límite solicitado o hasta que no haya más resultados
            for call_num in range(api_calls_needed):
                # Calcular el límite para esta llamada (máximo 100)
                current_call_limit = min(100, original_limit - posts_collected)
                
                if current_call_limit <= 0:
                    break
                    
                # Parámetros para la búsqueda
                # Asegurarnos de que el límite nunca sea mayor que 100 (límite de la API)
                api_limit = min(100, current_call_limit)
                search_params = {
                    "q": search_query,
                    "limit": api_limit,
                    "sort": kwargs.get('sort', 'latest')  # Orden por defecto: más recientes primero
                }
                
                # Añadir cursor si no es la primera llamada
                if cursor:
                    search_params["cursor"] = cursor
                
                # Mostrar progreso para llamadas múltiples
                if api_calls_needed > 1:
                    print(f"🔍 Realizando llamada {call_num + 1} de ~{api_calls_needed} (obteniendo {current_call_limit} posts)")
                
                # Realizar la búsqueda
                search_results = self.client.app.bsky.feed.search_posts(search_params)
                
                # Guardar el cursor para la siguiente página si existe
                cursor = getattr(search_results, 'cursor', None)
                
                # Si no hay resultados o cursor, terminar el bucle
                if not hasattr(search_results, 'posts') or len(search_results.posts) == 0:
                    if call_num == 0:
                        print("⚠️ No se encontraron posts que coincidan con la búsqueda")
                    break
                
                # Procesar los resultados de esta página
                page_posts = []
                for post in search_results.posts:
                    # Extraer información relevante (mismo formato que get_user_posts)
                    post_data = {
                        'uri': post.uri,
                        'cid': post.cid,
                        'web_url': self.get_web_url_from_uri(post.uri, post.author.handle),
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
                    if hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images') and post.record.embed.images is not None:
                        # Extraer URLs de las imágenes en lugar de textos alternativos
                        image_urls = []
                        
                        # Eliminar debug para la versión final
                        
                        for img in post.record.embed.images:
                            if hasattr(img, 'image'):
                                # Intentar obtener CID válido
                                img_obj = img.image
                                cid = None
                                
                                # Extraer CID como string para la URL
                                if hasattr(img_obj, 'cid') and img_obj.cid:
                                    # Convertir el objeto CID a string
                                    cid_str = str(img_obj.cid)
                                    author_did = post.author.did
                                    # Construir URL usando el CID válido como string
                                    image_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={cid_str}"
                                    image_urls.append(image_url)
                        
                        # Solo añadir el campo 'images' si hay URLs válidas
                        if image_urls:
                            post_data['images'] = image_urls
                    
                    # Determinar el tipo de post
                    # Verificar primero si es un reply basado en la existencia de un atributo reply con valor no nulo
                    if hasattr(post.record, 'reply') and post.record.reply is not None:
                        post_data['post_type'] = 'reply'
                    else:
                        # Para los posts que no son replies, verificar si son reposts
                        # En el contexto de search_posts, no podemos hacer la comparación de autor vs. usuario
                        # ya que estamos buscando posts de cualquier usuario
                        
                        # Extraer los usuarios de interés de los parámetros
                        from_user = kwargs.get('from_user')
                        users_of_interest = []
                        if from_user:
                            # Si tenemos un from_user especificado, ese es nuestro usuario de interés
                            users_of_interest.append(from_user)
                            
                        # Si el autor del post está en nuestra lista de interés, es un original
                        # De lo contrario, podría ser un repost
                        author_handle = post.author.handle
                        
                        if users_of_interest and any(user.lower() in author_handle.lower() for user in users_of_interest):
                            # El autor está en nuestra lista de interés
                            post_data['post_type'] = 'original'
                        else:
                            # Podría ser un repost o simplemente un post de otro usuario
                            # Verificar otros indicadores de repost
                            if hasattr(post, 'reason') and post.reason is not None:
                                if hasattr(post.reason, 'py_type') and 'repost' in str(post.reason.py_type).lower():
                                    post_data['post_type'] = 'repost'
                                else:
                                    post_data['post_type'] = 'original'
                            else:
                                post_data['post_type'] = 'original'
                    
                    # Extraer URLs del contenido del post (dos métodos)
                    urls = []
                    
                    # Extraer menciones de usuarios
                    mentions = []
                    
                    # Extraer URLs y menciones de facets (formato estructurado de Bluesky)
                    if hasattr(post.record, 'facets') and post.record.facets:
                        for facet in post.record.facets:
                            if hasattr(facet, 'features'):
                                for feature in facet.features:
                                    # Identificar el tipo de feature según su py_type
                                    if hasattr(feature, 'py_type'):
                                        # Extraer links
                                        if feature.py_type == 'app.bsky.richtext.facet#link' and hasattr(feature, 'uri'):
                                            urls.append(feature.uri)
                                        # Extraer menciones
                                        elif feature.py_type == 'app.bsky.richtext.facet#mention' and hasattr(feature, 'did'):
                                            # Intentar obtener el handle si está disponible
                                            if hasattr(feature, 'handle'):
                                                mentions.append(feature.handle)
                                            else:
                                                mentions.append(feature.did)
                    
                    # 2. Como respaldo, también buscar URLs con regex en el texto
                    import re
                    url_pattern = r'https?://[\w\-\.]+(?:/[\w\-\./%?&=+#]*)?'
                    if post.record.text:
                        regex_urls = re.findall(url_pattern, post.record.text)
                        # Añadir URLs que no se hayan encontrado en facets
                        for url in regex_urls:
                            if url not in urls:
                                urls.append(url)
                    
                    # Almacenar URLs si se encontraron
                    if urls:
                        post_data['urls'] = urls
                        
                    # Almacenar menciones si se encontraron
                    if mentions:
                        post_data['mentions'] = mentions
                    
                    page_posts.append(post_data)
                
                # Añadir los posts de esta página a la lista completa
                posts.extend(page_posts)
                posts_collected += len(page_posts)
                
                # Mostrar progreso
                if api_calls_needed > 1:
                    print(f"ℹ️ Obtenidos {posts_collected} de {original_limit} posts solicitados")
                
                # Si no hay cursor o ya hemos alcanzado el límite, terminar
                if not cursor or posts_collected >= original_limit:
                    break
                    time.sleep(0.5)  # Pausa de medio segundo entre llamadas
            
            print(f"✅ Encontrados un total de {len(posts)} posts que coinciden con la búsqueda")
            return posts
            
        except Exception as e:
            print(f"❌ Error al buscar posts: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_posts_from_search(self, query: str, limit: int = 50, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtiene posts de una búsqueda y los organiza por autor.
        Soporta obtener más de 100 posts mediante paginación automática.
        
        Args:
            query: Texto a buscar
            limit: Número máximo de resultados (puede ser mayor a 100, se usará paginación)
            **kwargs: Parámetros adicionales de búsqueda
            
        Returns:
            Dict: Diccionario con los posts organizados por autor
        """
        # La función search_posts ya maneja la paginación internamente
        search_posts = self.search_posts(query, limit, **kwargs)
        if not search_posts:
            return {}
        
        # Organizar los posts por autor
        results = {}
        for post in search_posts:
            author_handle = post['author']['handle']
            if author_handle not in results:
                results[author_handle] = []
            results[author_handle].append(post)
        
        print(f"📊 Posts organizados por autor: {len(results)} autores diferentes")
        return results
        
    def export_results(self, results: Dict[str, List[Dict[str, Any]]], format: str = 'json', filename: str = None, sort_by_date: bool = True) -> Optional[str]:
        """
        Exporta los resultados en el formato especificado.
        
        Args:
            results: Diccionario con los resultados
            format: Formato de exportación ('json', 'csv' o 'parquet')
            filename: Nombre del archivo (opcional)
            sort_by_date: Si es True, ordena los posts por fecha de creación (más recientes primero)
            
        Returns:
            str: Ruta del archivo guardado, o None si hubo un error
        """
        format = format.lower()
        
        if format == 'json':
            return self.save_results_to_json(results, filename)
        elif format == 'csv':
            return self.save_results_to_csv(results, filename, sort_by_date=sort_by_date)
        elif format == 'parquet':
            return self.save_results_to_parquet(results, filename, sort_by_date=sort_by_date)
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
    parser.add_argument('-b', '--bsky-list', help='URL de una lista de Bluesky (ej: https://bsky.app/profile/usuario/lists/123abc)')
    parser.add_argument('-s', '--search', help='Buscar posts (usar comillas para frases exactas)')
    parser.add_argument('--from', dest='from_user', help='Buscar posts de un usuario específico')
    parser.add_argument('--mention', help='Buscar posts que mencionan a un usuario específico')
    parser.add_argument('--lang', help='Buscar posts en un idioma específico (ej: es, en, fr)')
    parser.add_argument('--since', help='Buscar posts desde una fecha (formato: YYYY-MM-DD)')
    parser.add_argument('--until', help='Buscar posts hasta una fecha (formato: YYYY-MM-DD)')
    parser.add_argument('--domain', help='Buscar posts que contienen enlaces a un dominio específico')
    parser.add_argument('-n', '--limit', type=int, default=20, help='Número máximo de posts por usuario o búsqueda (con paginación para más de 100)')
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
    
    # Iniciar el proceso
    fetcher = BlueskyPostsFetcher(args.username, args.password)
    
    # Si se especificó una búsqueda, esta tiene prioridad
    if args.search:
        # Construir parámetros de búsqueda
        search_params = {
            'from_user': args.from_user,
            'mention': args.mention,
            'language': args.lang,
            'since': args.since,
            'until': args.until,
            'domain': args.domain
        }
        results = fetcher.get_posts_from_search(args.search, args.limit, **search_params)
    # Si no hay búsqueda pero hay una URL de lista, obtener posts de esa lista
    elif args.bsky_list:
        results = fetcher.get_posts_from_bluesky_list_url(args.bsky_list, args.limit)
    else:
        # Si todavía no hay usuarios, pedir al usuario
        if not handles:
            print("⚠️ No se ha especificado ninguna lista de usuarios ni búsqueda.")
            user_input = input("Ingresa usuarios separados por comas, una URL de lista de Bluesky, o una búsqueda con 'buscar:': ")
            
            # Verificar si es una búsqueda
            if user_input.startswith('buscar:'):
                search_query = user_input.replace('buscar:', '').strip()
                results = fetcher.get_posts_from_search(search_query, args.limit)
            # Verificar si es una URL de lista de Bluesky
            elif "bsky.app/profile" in user_input and "/lists/" in user_input:
                results = fetcher.get_posts_from_bluesky_list_url(user_input, args.limit)
            # De lo contrario, asumir que son usuarios
            else:
                handles = [h.strip() for h in user_input.split(',') if h.strip()]
                results = fetcher.get_posts_from_users(handles, args.limit)
        else:
            results = fetcher.get_posts_from_users(handles, args.limit)
    
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
