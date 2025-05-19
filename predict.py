from cog import BasePredictor, Input, Path
from piper.voice import PiperVoice # L'importation principale pour utiliser Piper
import wave # Pour manipuler les fichiers WAV
import io   # Pour manipuler les flux de données en mémoire
import os   # Pour manipuler les chemins de fichiers
from pydub import AudioSegment # <<< NOUVEAU : Importer AudioSegment de pydub


class Predictor(BasePredictor):
    def setup(self):
        """
        Cette méthode est appelée une seule fois au démarrage du conteneur Cog.
        C'est ici que vous chargez vos modèles Piper.
        """
        self.voices = {} # Un dictionnaire pour stocker les différentes voix

        # --- Définissez ici les voix que vous voulez charger ---
        # Pour chaque voix, spécifiez un identifiant unique et les chemins vers ses fichiers.
        # Assurez-vous que ces fichiers .onnx et .onnx.json sont présents dans votre dépôt
        # aux chemins spécifiés (par exemple, dans le dossier 'piper_voices').

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
            },
            
            # Ajoutez d'autres voix ici en suivant le même format
        }

        for voice_id, paths in voices_to_load.items():
            model_path = paths["model_path"]
            config_path = paths["config_path"]
            if os.path.exists(model_path) and os.path.exists(config_path):
                print(f"Chargement de la voix '{voice_id}' depuis : {model_path}")
                self.voices[voice_id] = PiperVoice(model_path, config_path)
            else:
                print(f"AVERTISSEMENT: Modèle ou configuration pour la voix '{voice_id}' non trouvé...")
        if not self.voices:
            raise RuntimeError("Aucun modèle vocal n'a pu être chargé...")
        print(f"Modèles Piper chargés. Voix disponibles : {list(self.voices.keys())}")

    def predict(
        self,
        text: str = Input(description="Le texte à convertir en parole."),
        voice_id: str = Input(
            description="Identifiant de la voix à utiliser.",
            default="ru_RU_irina",
            choices=["ru_RU_irina"] # Mettez à jour avec vos voice_id
        ),
        output_format: str = Input( # <<< NOUVEAU (Optionnel) : Permettre de choisir le format
            description="Format de sortie audio désiré.",
            default="mp3",
            choices=["wav", "mp3"]
        ),
        bitrate: str = Input( # <<< NOUVEAU (Optionnel) : Débit pour MP3
            description="Débit pour l'encodage MP3 (ex: '128k', '192k', '256k').",
            default="192k" # Bon compromis qualité/taille pour la voix
        )
    ) -> Path:
        if voice_id not in self.voices:
            raise ValueError(f"Voix non supportée : '{voice_id}'. Disponibles : {list(self.voices.keys())}")

        selected_voice = self.voices[voice_id]
        wav_audio_buffer = io.BytesIO()

        with wave.open(wav_audio_buffer, 'wb') as wf:
            selected_voice.synthesize(text, wf)
        wav_audio_buffer.seek(0) # Important: rembobiner après écriture

        if output_format.lower() == "mp3":
            # Convertir le WAV en mémoire en MP3 en mémoire
            audio_segment = AudioSegment.from_wav(wav_audio_buffer)
            
            mp3_audio_buffer = io.BytesIO()
            audio_segment.export(mp3_audio_buffer, format="mp3", bitrate=bitrate)
            mp3_audio_buffer.seek(0)

            output_path = "/tmp/output.mp3"
            with open(output_path, "wb") as f_out:
                f_out.write(mp3_audio_buffer.read())
            print(f"Audio MP3 généré : '{text}' voix '{voice_id}', bitrate '{bitrate}', sauvegardé dans {output_path}")

        elif output_format.lower() == "wav":
            output_path = "/tmp/output.wav"
            with open(output_path, "wb") as f_out:
                f_out.write(wav_audio_buffer.read())
            print(f"Audio WAV généré : '{text}' voix '{voice_id}', sauvegardé dans {output_path}")
        
        else:
            raise ValueError(f"Format de sortie non supporté : {output_format}. Choisissez 'wav' ou 'mp3'.")
            
        return Path(output_path)
