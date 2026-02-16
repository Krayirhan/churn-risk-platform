# ============================================================================
# model_evaluation.py — Model Değerlendirme ve Detaylı Raporlama Bileşeni
# ============================================================================
# NEDEN BU DOSYA VAR?
#   model_trainer.py modeli eğitip F1 ile seçer ama detaylı değerlendirme
#   bu dosyanın işi. Trainer "karar verir", Evaluator "raporlar".
#
# NE ÜRETİR?
#   1. Classification Report: Her sınıf için precision/recall/f1/support
#   2. Confusion Matrix: TP, FP, TN, FN sayıları
#   3. ROC-AUC ve PR-AUC (Precision-Recall AUC)
#   4. Feature Importance (model destekliyorsa)
#   5. Tüm bunları artifacts/metrics.json ve artifacts/confusion_matrix.json'a yazar
#
# NEDEN PR-AUC DA HESAPLANIYOR?
#   Churn verisi dengesiz (%27 churn). Dengesiz veride:
#   - ROC-AUC iyimser olabilir (negatif sınıf çok olduğu için TN yüksek çıkar)
#   - PR-AUC sadece pozitif sınıfa (Churn=1) odaklanır → daha dürüst metrik
#
# ÇAĞRILIŞ ŞEKLİ:
#   train_pipeline.py → ModelEvaluation().initiate(model, X_test, y_test)
# ============================================================================

import os
import sys
import numpy as np
from dataclasses import dataclass

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    recall_score,
    precision_score,
    accuracy_score,
    roc_auc_score,
    average_precision_score,  # PR-AUC
    roc_curve,
    precision_recall_curve
)

from src.exception import CustomException
from src.logger import logging
from src.utils.common import load_yaml, load_object, save_json


# ─────────────────────────────────────────────────────────────────────────────
# KONFİGÜRASYON
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ModelEvaluationConfig:
    """
    Değerlendirme sürecinin ayarları.
    """
    _cfg: dict = None

    def __post_init__(self):
        self._cfg = load_yaml("configs/config.yaml")

        artifacts = self._cfg.get("artifacts", {})

        # Kayıtlı modelin yolu (zaten eğitilmiş)
        self.model_path: str = artifacts.get("model_path", "artifacts/model.pkl")

        # Metriklerin kaydedileceği yollar
        self.metrics_path: str = artifacts.get("metrics_path", "artifacts/metrics.json")
        self.confusion_matrix_path: str = artifacts.get(
            "confusion_matrix_path", "artifacts/confusion_matrix.json"
        )

        # Hedef sütun ismi (raporda kullanılacak)
        self.target_col: str = self._cfg.get("target_col", "Churn")


# ─────────────────────────────────────────────────────────────────────────────
# ANA SINIF
# ─────────────────────────────────────────────────────────────────────────────

class ModelEvaluation:
    """
    Eğitilmiş modeli test verisi üzerinde kapsamlı şekilde değerlendirir.
    
    Ürettiği çıktılar:
      - artifacts/metrics.json: Tüm metrikler
      - artifacts/confusion_matrix.json: Confusion matrix detayı
      - Console'a classification report ve özet tablo yazdırır
    """

    def __init__(self):
        self.config = ModelEvaluationConfig()

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray = None) -> dict:
        """
        Tüm değerlendirme metriklerini hesaplar.
        
        Args:
            y_true: Gerçek etiketler (0/1)
            y_pred: Tahmin edilen etiketler (0/1)
            y_proba: Pozitif sınıf olasılıkları (0.0-1.0) — ROC/PR için
        
        Returns:
            dict: Tüm metrikler
        """
        metrics = {}

        # ─── TEMEL METRİKLER ───
        
        # ACCURACY: Doğru tahmin oranı (TP + TN) / (TP + TN + FP + FN)
        # ⚠ Dengesiz veride yanıltıcı! %73 "hep No de" bile %73 verir.
        metrics["accuracy"] = round(accuracy_score(y_true, y_pred), 4)

        # F1-SCORE: Precision ve Recall'ın harmonik ortalaması
        # F1 = 2 × (P × R) / (P + R)
        # NEDEN HARMONİK? Aritmetik ortalama P=1, R=0 durumunda 0.5 verir
        # ama harmonik ortalama 0 verir → daha dürüst.
        metrics["f1"] = round(f1_score(y_true, y_pred), 4)

        # RECALL (Sensitivity / TPR): Gerçek churn'lerin ne kadarını yakaladık?
        # Recall = TP / (TP + FN)
        # NEDEN ÖNEMLİ? Churn eden müşteriyi kaçırmak = gelir kaybı.
        # Recall düşükse → churn edecek müşterileri tespit edemiyoruz.
        metrics["recall"] = round(recall_score(y_true, y_pred), 4)

        # PRECISION: "Churn" dediğimiz müşterilerin ne kadarı gerçekten churn?
        # Precision = TP / (TP + FP)
        # NEDEN ÖNEMLİ? Precision düşükse → yanlış alarma maliyet (gereksiz kampanya).
        metrics["precision"] = round(precision_score(y_true, y_pred), 4)

        # ─── OLABILIRLIK BAZLI METRİKLER ───
        
        if y_proba is not None:
            # ROC-AUC: ROC eğrisinin altında kalan alan
            # 0.5 = rastgele tahmin, 1.0 = mükemmel ayrım
            # Eşikten bağımsız bir metrik → "model ne kadar iyi ayırt ediyor?"
            metrics["roc_auc"] = round(roc_auc_score(y_true, y_proba), 4)

            # PR-AUC (Average Precision): Precision-Recall eğrisinin altındaki alan
            # NEDEN PR-AUC?
            #   Dengesiz veride ROC-AUC iyimser olabilir çünkü TN çok yüksek.
            #   PR-AUC sadece pozitif sınıfa odaklanır → daha güvenilir.
            #   PR-AUC > 0.5 ise model "şanstan" iyidir (dengesiz veride).
            metrics["pr_auc"] = round(average_precision_score(y_true, y_proba), 4)

            # ROC eğrisi noktaları (opsiyonel dashboard için)
            fpr, tpr, roc_thresholds = roc_curve(y_true, y_proba)
            metrics["roc_curve"] = {
                "fpr": [round(x, 4) for x in fpr.tolist()],
                "tpr": [round(x, 4) for x in tpr.tolist()],
            }

            # PR eğrisi noktaları
            pr_precision, pr_recall, pr_thresholds = precision_recall_curve(y_true, y_proba)
            metrics["pr_curve"] = {
                "precision": [round(x, 4) for x in pr_precision.tolist()],
                "recall": [round(x, 4) for x in pr_recall.tolist()],
            }

        return metrics

    def _compute_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        """
        Confusion Matrix hesaplar ve yorumlu dict olarak döndürür.
        
        CONFUSION MATRIX NEDİR?
          Tahmin edilen vs gerçek etiketlerin 2×2 tablosu:
          
                          Tahmin: No    Tahmin: Yes
          Gerçek: No        TN             FP         ← FP = Yanlış Alarm
          Gerçek: Yes       FN             TP         ← FN = Kaçırılan Churn!
        
        İŞ YORUMU:
          - FN (False Negative): Churn edecek müşteriyi "kalmaya devam edecek" dedik.
            BU EN TEHLİKELİ HATA! Müşteriyi kaybederiz ve önlem alamayız.
          - FP (False Positive): Kalmaya devam edecek müşteriye "churn edecek" dedik.
            Daha az tehlikeli: gereksiz kampanya maliyeti ama müşteriyi kaybetmeyiz.
        
        Returns:
            dict: TN, FP, FN, TP sayıları ve oranları
        """
        cm = confusion_matrix(y_true, y_pred)

        # [[TN, FP],
        #  [FN, TP]]
        tn, fp, fn, tp = cm.ravel()
        total = len(y_true)

        cm_dict = {
            # Ham sayılar
            "true_negative": int(tn),     # Doğru "No Churn" tahmini
            "false_positive": int(fp),    # Yanlış "Churn" alarmı
            "false_negative": int(fn),    # Kaçırılan churn (TEHLİKELİ!)
            "true_positive": int(tp),     # Doğru "Churn" tahmini

            # Oranlar (toplam üzerinden)
            "tn_rate": round(tn / total, 4),
            "fp_rate": round(fp / total, 4),
            "fn_rate": round(fn / total, 4),
            "tp_rate": round(tp / total, 4),

            # Confusion matrix'in düz hali (2D array olarak)
            "matrix": cm.tolist(),

            # İş metrikleri
            "total_samples": int(total),
            "total_actual_churn": int(tp + fn),       # Gerçekte churn eden
            "total_actual_no_churn": int(tn + fp),    # Gerçekte kalan
            "total_predicted_churn": int(tp + fp),    # "Churn" dediğimiz
            "total_predicted_no_churn": int(tn + fn), # "No Churn" dediğimiz
        }

        return cm_dict

    def initiate(
        self,
        model=None,
        X_test: np.ndarray = None,
        y_test: np.ndarray = None,
        model_name: str = "best_model"
    ) -> dict:
        """
        Model değerlendirme sürecini başlatır.
        
        AKIŞ:
          1. Model verilmemişse → artifacts/model.pkl'den yükle
          2. Test verisi üzerinde tahmin yap (predict + predict_proba)
          3. Tüm metrikleri hesapla (F1, Recall, AUC, PR-AUC vb.)
          4. Confusion matrix hesapla
          5. Classification report yazdır
          6. Sonuçları JSON olarak kaydet
        
        Args:
            model: Eğitilmiş model nesnesi (None ise diskten yüklenir)
            X_test: Test feature matrisi
            y_test: Test hedef vektörü
            model_name: Raporda kullanılacak model ismi
        
        Returns:
            dict: Tüm metrikler ve confusion matrix
        """
        try:
            logging.info("=" * 60)
            logging.info("MODEL EVALUATION başlatılıyor...")
            logging.info("=" * 60)

            # ─── ADIM 1: Modeli Yükle (gerekirse) ───
            if model is None:
                logging.info(f"Model diskten yükleniyor: {self.config.model_path}")
                model = load_object(self.config.model_path)

            # ─── ADIM 2: Tahmin Yap ───
            logging.info(f"Test verisi üzerinde tahmin yapılıyor (n={len(y_test)})...")

            # Sınıf tahmini (0 veya 1)
            y_pred = model.predict(X_test)

            # Olasılık tahmini (ROC-AUC ve PR-AUC için gerekli)
            # predict_proba → [[P(No), P(Yes)], ...] → [:, 1] = P(Yes)
            y_proba = None
            try:
                y_proba = model.predict_proba(X_test)[:, 1]
            except (AttributeError, IndexError):
                logging.warning("⚠ Model predict_proba desteklemiyor, olasılık bazlı metrikler atlanacak.")

            # ─── ADIM 3: Metrikleri Hesapla ───
            logging.info("Metrikler hesaplanıyor...")
            metrics = self._compute_metrics(y_true=y_test, y_pred=y_pred, y_proba=y_proba)
            metrics["model_name"] = model_name

            # ─── ADIM 4: Confusion Matrix ───
            logging.info("Confusion matrix hesaplanıyor...")
            cm_dict = self._compute_confusion_matrix(y_true=y_test, y_pred=y_pred)

            # ─── ADIM 5: Classification Report (konsola yazdır) ───
            # sklearn'ın classification_report'u her sınıf için detaylı tablo verir
            cls_report = classification_report(
                y_test, y_pred,
                target_names=["No Churn (0)", "Churn (1)"],
                digits=4
            )
            logging.info(f"\nClassification Report:\n{cls_report}")

            # ─── ADIM 6: Sonuçları Kaydet ───
            # Metrikleri JSON'a yaz (dashboard ve karşılaştırma için)
            eval_result = {
                "model_name": model_name,
                "metrics": {
                    "accuracy": metrics["accuracy"],
                    "f1": metrics["f1"],
                    "recall": metrics["recall"],
                    "precision": metrics["precision"],
                    "roc_auc": metrics.get("roc_auc"),
                    "pr_auc": metrics.get("pr_auc"),
                },
                "confusion_matrix": cm_dict,
            }

            # ROC ve PR eğrilerini ayrı tutabiliriz (büyük olabilir)
            if "roc_curve" in metrics:
                eval_result["curves"] = {
                    "roc": metrics["roc_curve"],
                    "pr": metrics["pr_curve"],
                }

            save_json(eval_result, self.config.metrics_path)
            save_json(cm_dict, self.config.confusion_matrix_path)

            # ─── Konsola Özet Yazdır ───
            self._print_summary(metrics, cm_dict, model_name)

            logging.info("MODEL EVALUATION tamamlandı.")
            logging.info("=" * 60)

            return eval_result

        except Exception as e:
            raise CustomException(e, sys)

    @staticmethod
    def _print_summary(metrics: dict, cm: dict, model_name: str) -> None:
        """
        Değerlendirme özetini güzel formatla konsola yazdırır.
        """
        print("\n" + "=" * 60)
        print(f"📊 MODEL DEĞERLENDİRME RAPORU — {model_name}")
        print("=" * 60)

        print(f"\n  📈 Performans Metrikleri:")
        print(f"     Accuracy    : {metrics['accuracy']:.4f}")
        print(f"     F1-Score    : {metrics['f1']:.4f}")
        print(f"     Recall      : {metrics['recall']:.4f}")
        print(f"     Precision   : {metrics['precision']:.4f}")
        if "roc_auc" in metrics:
            print(f"     ROC-AUC     : {metrics['roc_auc']:.4f}")
        if "pr_auc" in metrics:
            print(f"     PR-AUC      : {metrics['pr_auc']:.4f}")

        print(f"\n  📋 Confusion Matrix:")
        print(f"     {'':>20} Tahmin: No   Tahmin: Yes")
        print(f"     {'Gerçek: No':>20}    {cm['true_negative']:>5}        {cm['false_positive']:>5}")
        print(f"     {'Gerçek: Yes':>20}    {cm['false_negative']:>5}        {cm['true_positive']:>5}")

        print(f"\n  💡 İş Yorumu:")
        print(f"     Toplam test verisi       : {cm['total_samples']}")
        print(f"     Gerçek churn sayısı      : {cm['total_actual_churn']}")
        print(f"     Doğru yakalanan churn    : {cm['true_positive']} "
              f"(Recall: {metrics['recall']:.1%})")
        print(f"     Kaçırılan churn (FN)     : {cm['false_negative']} "
              f"⚠ Bu müşteriler kaybolacak!")
        print(f"     Yanlış alarm (FP)        : {cm['false_positive']} "
              f"(gereksiz kampanya maliyeti)")
        print("=" * 60 + "\n")

