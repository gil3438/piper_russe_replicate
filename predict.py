from cog import BasePredictor, Input, Path
from piper.voice import PiperVoice # L'importation principale pour utiliser Piper
import wave # Pour manipuler les fichiers WAV
import io   # Pour manipuler les flux de données en mémoire
import os   # Pour manipuler les chemins de fichiers
from pydub import AudioSegment # Pour la conversion en MP3
import json # Ajouté pour le débogage du contenu JSON

class Predictor(BasePredictor):
    def setup(self):
        """
        Cette méthode est appelée une seule fois au démarrage du conteneur Cog.
        C'est ici que vous chargez vos modèles Piper.
        """
        self.voices = {} # Un dictionnaire pour stocker les différentes voix
        print("--- DÉBUT DE LA MÉTHODE SETUP ---")

        # --- Définissez ici les voix que vous voulez charger ---
        voices_to_load = {
            "ru_RU_irina": { # Identifiant unique pour cette voix
                "model_path": "piper_voices/ru_RU/irina/ru_RU-irina-medium.onnx",
                "config_path": "piper_voices/ru_RU/irina/ru_RU-irina-medium.onnx.json"
            },
            "ru_RU_dmitri": { # Une autre voix russe
                "model_path": "piper_voices/ru_RU/dmitri/ru_RU-dmitri-medium.onnx",
                "config_path": "piper_voices/ru_RU/dmitri/ru_RU-dmitri-medium.onnx.json"
            },
            "ru_RU_ruslan": { # Une autre voix russe
                "model_path": "piper_voices/ru_RU/ruslan/ru_RU-ruslan-medium.onnx",
                "config_path": "piper_voices/ru_RU/ruslan/ru_RU-ruslan-medium.onnx.json"
            }
            # Ajoutez d'autres voix ici en suivant le même format
        }

        for voice_id, paths in voices_to_load.items():
            model_path = paths["model_path"]
            config_path = paths["config_path"]
            print(f"Pour voice_id '{voice_id}':")
            print(f"  Chemin modèle attendu : {model_path}")
            print(f"  Chemin config attendu : {config_path}")

            model_exists = os.path.exists(model_path)
            config_exists = os.path.exists(config_path)
            print(f"  Le fichier modèle existe : {model_exists}")
            print(f"  Le fichier config existe : {config_exists}")

            if model_exists and config_exists:
                print(f"  Tentative de lecture et de parsing du fichier config : {config_path}")
                try:
                    with open(config_path, "r", encoding="utf-8") as f_config:
                        config_content_preview = f_config.read(500) # Lire les 500 premiers caractères
                        print(f"    Aperçu du contenu de {config_path} (500 premiers car.):\n{config_content_preview}\n    --- Fin de l'aperçu ---")
                        f_config.seek(0) # Rembobiner pour que Piper puisse le lire
                        # Tentative de charger le JSON ici pour un diagnostic précoce
                        json_data = json.load(f_config)
                        print(f"    Fichier {config_path} chargé comme JSON avec succès. Type: {type(json_data)}")
                        if isinstance(json_data, dict) and "audio" in json_data and "sample_rate" in json_data["audio"]:
                            print(f"    Sample rate trouvé dans JSON via lecture directe: {json_data['audio']['sample_rate']}")
                        else:
                            print(f"    AVERTISSEMENT: Structure JSON ('audio' et 'sample_rate') non trouvée dans {config_path} lors de la lecture directe.")
                except Exception as e:
                    print(f"    ERREUR en lisant ou en parsant {config_path} directement : {e}")
                    # Si la lecture directe échoue, PiperVoice pourrait aussi échouer.
                    # On continue pour voir si PiperVoice lève une erreur plus spécifique.

                print(f"  Initialisation de PiperVoice pour '{voice_id}'...")
                try:
                    voice_instance = PiperVoice(config_path=config_path, model_path=model_path)
                    self.voices[voice_id] = voice_instance
                    # Vérifiez le type de l'attribut config APRÈS l'initialisation de PiperVoice
                    if hasattr(voice_instance, 'config'):
                        print(f"    PiperVoice pour '{voice_id}' initialisé. Type de voice_instance.config : {type(voice_instance.config)}")
                        if isinstance(voice_instance.config, str):
                            print(f"    !!! ALERTE: voice_instance.config EST UNE CHAÎNE DE CARACTÈRES POUR '{voice_id}' !!! Contenu: {voice_instance.config}")
                        elif hasattr(voice_instance.config, 'sample_rate'): # Vérifie si c'est un objet config valide
                            print(f"    voice_instance.config.sample_rate pour '{voice_id}': {voice_instance.config.sample_rate}")
                        else:
                            print(f"    voice_instance.config pour '{voice_id}' n'a pas d'attribut 'sample_rate'. Attributs disponibles: {dir(voice_instance.config)}")
                    else:
                         print(f"    PiperVoice pour '{voice_id}' initialisé, mais n'a PAS d'attribut 'config'.")
                except Exception as e:
                    print(f"    ERREUR lors de l'initialisation de PiperVoice pour '{voice_id}': {e}")

            else:
                print(f"  AVERTISSEMENT: Modèle OU configuration pour la voix '{voice_id}' non trouvé. Cette voix sera ignorée.")

        if not self.voices:
            raise RuntimeError("Aucun modèle vocal n'a pu être chargé correctement. Le service ne peut pas démarrer.")
        
        print(f"--- FIN DE LA MÉTHODE SETUP --- Voix réellement chargées et disponibles : {list(self.voices.keys())}")

    def predict(
        self,
        text: str = Input(description="Le texte à convertir en parole."),
        voice_id: str = Input(
            description="Identifiant de la voix à utiliser.",
            default="ru_RU_irina", # Assurez-vous que cette voix par défaut est bien chargée
            # IMPORTANT: Mettez à jour cette liste avec TOUS les voice_id que vous avez définis et qui sont chargés avec succès !
            choices=["ru_RU_irina", "ru_RU_dmitri", "ru_RU_ruslan"] 
        ),
        output_format: str = Input(
            description="Format de sortie audio désiré.",
            default="mp3",
            choices=["wav", "mp3"]
        ),
        bitrate: str = Input(
            description="Débit pour l'encodage MP3 (ex: '128k', '192k', '256k').",
            default="192k"
        )
    ) -> Path:
        print(f"--- DÉBUT DE LA MÉTHODE PREDICT ---")
        print(f"Requête reçue -> voice_id: '{voice_id}', output_format: '{output_format}', bitrate: '{bitrate}', texte: '{text[:50]}...' (tronqué si long)")

        if voice_id not in self.voices:
            print(f"Erreur dans PREDICT: voice_id '{voice_id}' non trouvé dans self.voices. Voix disponibles: {list(self.voices.keys())}")
            raise ValueError(f"Voix non supportée ou modèle non chargé : '{voice_id}'. Voix disponibles : {list(self.voices.keys())}")

        selected_voice = self.voices[voice_id]
        print(f"Voix sélectionnée pour la synthèse: {selected_voice} (type: {type(selected_voice)})")
        
        # Vérification cruciale de selected_voice.config avant d'appeler synthesize
        if hasattr(selected_voice, 'config'):
            print(f"  Dans PREDICT, AVANT synthesize, type de selected_voice.config : {type(selected_voice.config)}")
            if isinstance(selected_voice.config, str):
                 print(f"  !!! ALERTE DANS PREDICT: selected_voice.config EST UNE CHAÎNE DE CARACTÈRES !!! Contenu: {selected_voice.config}")
                 raise TypeError(f"Erreur de configuration interne: l'attribut 'config' pour la voix '{voice_id}' est une chaîne et non un objet de configuration.")
            elif not hasattr(selected_voice.config, 'sample_rate'):
                 print(f"  !!! ALERTE DANS PREDICT: selected_voice.config n'a pas d'attribut 'sample_rate'. Attributs: {dir(selected_voice.config)}")
                 raise AttributeError(f"Erreur de configuration interne: l'attribut 'config' pour la voix '{voice_id}' n'a pas de 'sample_rate'.")
            else:
                print(f"  Dans PREDICT, AVANT synthesize, selected_voice.config.sample_rate OK: {selected_voice.config.sample_rate}")
        else:
            print(f"  !!! ALERTE DANS PREDICT: selected_voice (pour '{voice_id}') n'a pas d'attribut 'config'.")
            raise AttributeError(f"Erreur de configuration interne: l'objet voix sélectionné pour '{voice_id}' n'a pas d'attribut 'config'.")

        wav_audio_buffer = io.BytesIO()

        print(f"  Appel de selected_voice.synthesize pour la voix '{voice_id}'...")
        with wave.open(wav_audio_buffer, 'wb') as wf:
            selected_voice.synthesize(text, wf)
        wav_audio_buffer.seek(0) # Important: rembobiner après écriture
        print(f"  Synthèse WAV en mémoire terminée pour la voix '{voice_id}'.")

        if output_format.lower() == "mp3":
            print(f"  Conversion en MP3 avec bitrate '{bitrate}'...")
            audio_segment = AudioSegment.from_wav(wav_audio_buffer)
            mp3_audio_buffer = io.BytesIO()
            audio_segment.export(mp3_audio_buffer, format="mp3", bitrate=bitrate)
            mp3_audio_buffer.seek(0)
            output_path = "/tmp/output.mp3"
            with open(output_path, "wb") as f_out:
                f_out.write(mp3_audio_buffer.read())
            print(f"  Audio MP3 généré pour '{voice_id}', sauvegardé dans {output_path}")

        elif output_format.lower() == "wav":
            output_path = "/tmp/output.wav"
            with open(output_path, "wb") as f_out:
                f_out.write(wav_audio_buffer.read())
            print(f"  Audio WAV généré pour '{voice_id}', sauvegardé dans {output_path}")
        
        else:
            print(f"  Erreur: Format de sortie non supporté : {output_format}")
            raise ValueError(f"Format de sortie non supporté : {output_format}. Choisissez 'wav' ou 'mp3'.")
            
        print(f"--- FIN DE LA MÉTHODE PREDICT --- Retour du chemin: {output_path}")
        return Path(output_path)
