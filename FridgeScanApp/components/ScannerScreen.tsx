import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
  Alert,
  ActivityIndicator,
  Dimensions,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';
import { API_BASE_URL } from '../constants/config';

const { width } = Dimensions.get('window');

interface DetectedItem {
  id: string;
  name: string;
  category: string;
  quantity: number;
  unit: string;
  freshness_status: string;
  confidence_score?: number;
}

interface DetectionResult {
  items: DetectedItem[];
  total_detected: number;
  message: string;
  model1_results?: DetectedItem[];
  model2_results?: DetectedItem[];
}

const ScannerScreen: React.FC = () => {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [detectionResults, setDetectionResults] = useState<DetectionResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [addingToPantry, setAddingToPantry] = useState(false);
  const [itemQuantities, setItemQuantities] = useState<Map<string, number>>(new Map());

  const requestPermissions = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        'Permission Required',
        'Camera permission is required to scan your fridge.',
        [{ text: 'OK' }]
      );
      return false;
    }
    return true;
  };

  const pickImageFromGallery = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        setSelectedImage(result.assets[0].uri);
        setDetectionResults(null);
      }
    } catch (error) {
      console.error('Error picking image:', error);
      Alert.alert('Error', 'Failed to pick image from gallery.');
    }
  };

  const takePhoto = async () => {
    const hasPermission = await requestPermissions();
    if (!hasPermission) return;

    try {
      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        setSelectedImage(result.assets[0].uri);
        setDetectionResults(null);
      }
    } catch (error) {
      console.error('Error taking photo:', error);
      Alert.alert('Error', 'Failed to take photo.');
    }
  };

  const uploadAndScan = async () => {
    if (!selectedImage) {
      Alert.alert('No Image', 'Please select or take a photo first.');
      return;
    }

    setScanning(true);
    setUploading(true);

    try {
      // Create FormData
      const formData = new FormData();
      const filename = selectedImage.split('/').pop() || 'image.jpg';
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : `image/jpeg`;

      formData.append('file', {
        uri: selectedImage,
        name: filename,
        type: type,
      } as any);

      // Upload to backend
      const response = await axios.post<DetectionResult>(
        `${API_BASE_URL}/fridge/scan`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 30000, // 30 seconds
        }
      );

      setDetectionResults(response.data);
      
      // Initialize quantities from detection results - use item.id which should be unique
      const quantities = new Map<string, number>();
      if (response.data.model1_results) {
        response.data.model1_results.forEach((item) => {
          const key = item.id || `model1-${Date.now()}-${Math.random()}`;
          quantities.set(key, item.quantity || 1);
        });
      }
      if (response.data.model2_results) {
        response.data.model2_results.forEach((item) => {
          const key = item.id || `model2-${Date.now()}-${Math.random()}`;
          quantities.set(key, item.quantity || 1);
        });
      }
      setItemQuantities(quantities);
      
      Alert.alert('Success', `Detected ${response.data.total_detected} items!`);
    } catch (error: any) {
      console.error('Error scanning image:', error);
      let message = 'Unable to scan image. Products were not added.';

      if (axios.isAxiosError(error)) {
        if (error.response?.data?.detail) {
          message = `${error.response.data.detail}. Products were not added.`;
        } else if (error.message) {
          message = `${error.message}. Products were not added.`;
        }
      } else if (error instanceof Error) {
        message = `${error.message}. Products were not added.`;
      }

      setDetectionResults(null);
      Alert.alert('Scan Failed', message);
    } finally {
      setUploading(false);
      setScanning(false);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setDetectionResults(null);
    setSelectedItems(new Set());
    setItemQuantities(new Map());
  };

  const toggleItemSelection = (itemId: string) => {
    setSelectedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const selectAllItems = () => {
    if (detectionResults) {
      const allItems = [
        ...(detectionResults.model1_results || []).map((item) => item.id || `model1-${Date.now()}`),
        ...(detectionResults.model2_results || []).map((item) => item.id || `model2-${Date.now()}`),
      ];
      setSelectedItems(new Set(allItems));
    }
  };

  const deselectAllItems = () => {
    setSelectedItems(new Set());
  };

  const addSelectedToPantry = async () => {
    if (selectedItems.size === 0) {
      Alert.alert('No Items Selected', 'Please select at least one item to add to pantry.');
      return;
    }

    if (!detectionResults) return;

    setAddingToPantry(true);

    try {
      // Combine items from both models
      const allItems = [
        ...(detectionResults.model1_results || []).map((item) => ({ ...item, key: item.id || `model1-${Date.now()}` })),
        ...(detectionResults.model2_results || []).map((item) => ({ ...item, key: item.id || `model2-${Date.now()}` })),
      ];
      
      const itemsToAdd = allItems.filter((item) =>
        selectedItems.has(item.key)
      );

      // Add items to pantry one by one with updated quantities
      const promises = itemsToAdd.map((item) => {
        const quantity = itemQuantities.get(item.key) || item.quantity || 1;
        return axios.post(`${API_BASE_URL}/pantry/items`, {
          name: item.name,
          category: item.category || 'uncategorized',
          quantity: quantity,
          unit: item.unit || 'item',
          // expiry_date is optional, so we don't include it
        });
      });

      await Promise.all(promises);

      Alert.alert(
        'Success',
        `Successfully added ${itemsToAdd.length} item${itemsToAdd.length > 1 ? 's' : ''} to pantry!`,
        [
          {
            text: 'OK',
            onPress: () => {
              setSelectedItems(new Set());
            },
          },
        ]
      );
    } catch (error: any) {
      console.error('Error adding items to pantry:', error?.response?.data || error);
      const message =
        error?.response?.data?.detail ||
        'Failed to add items to pantry. Please try again.';
      Alert.alert('Error', message);
    } finally {
      setAddingToPantry(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Scan Your Fridge</Text>
          <Text style={styles.subtitle}>
            Take a photo or choose from gallery to detect ingredients
          </Text>
        </View>

        {/* Image Preview */}
        {selectedImage ? (
          <View style={styles.imageContainer}>
            <Image source={{ uri: selectedImage }} style={styles.previewImage} />
            <TouchableOpacity style={styles.clearButton} onPress={clearImage}>
              <Ionicons name="close-circle" size={30} color="#E74C3C" />
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.placeholderContainer}>
            <Ionicons name="camera-outline" size={80} color="#BDC3C7" />
            <Text style={styles.placeholderText}>No image selected</Text>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[styles.button, styles.galleryButton]}
            onPress={pickImageFromGallery}
            disabled={uploading}
          >
            <Ionicons name="images-outline" size={24} color="white" />
            <Text style={styles.buttonText}>From Gallery</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.cameraButton]}
            onPress={takePhoto}
            disabled={uploading}
          >
            <Ionicons name="camera" size={24} color="white" />
            <Text style={styles.buttonText}>Take Photo</Text>
          </TouchableOpacity>
        </View>

        {/* Scan Button */}
        {selectedImage && (
          <TouchableOpacity
            style={[styles.scanButton, uploading && styles.scanButtonDisabled]}
            onPress={uploadAndScan}
            disabled={uploading || scanning}
          >
            {scanning ? (
              <ActivityIndicator color="white" />
            ) : (
              <>
                <Ionicons name="scan-outline" size={24} color="white" />
                <Text style={styles.scanButtonText}>Scan for Ingredients</Text>
              </>
            )}
          </TouchableOpacity>
        )}

        {/* Detection Results - Model Comparison */}
        {detectionResults && (
          (detectionResults.model1_results && detectionResults.model1_results.length > 0) ||
          (detectionResults.model2_results && detectionResults.model2_results.length > 0) ||
          detectionResults.items.length > 0
        ) && (
          <View style={styles.resultsContainer}>
            <Text style={styles.resultsTitle}>Detection Results</Text>
            
            {/* Model 1 Results */}
            {detectionResults.model1_results && detectionResults.model1_results.length > 0 && (
              <View style={styles.modelSection}>
                <View style={styles.modelHeader}>
                  <Text style={styles.modelTitle}>Model 1 ({detectionResults.model1_results.length})</Text>
                </View>
                {detectionResults.model1_results.map((item, index) => {
                  const itemKey = item.id || `model1-${index}`;
                  const isSelected = selectedItems.has(itemKey);
                  return (
                    <TouchableOpacity
                      key={itemKey}
                      style={[
                        styles.resultItem,
                        isSelected && styles.resultItemSelected,
                      ]}
                      onPress={() => toggleItemSelection(itemKey)}
                      activeOpacity={0.7}
                    >
                      <View style={styles.resultItemCheckbox}>
                        <Ionicons
                          name={isSelected ? 'checkbox' : 'checkbox-outline'}
                          size={24}
                          color={isSelected ? '#2196F3' : '#BDC3C7'}
                        />
                      </View>
                      <View style={styles.resultItemContent}>
                        <View style={styles.resultItemLeft}>
                          <View style={styles.itemNameRow}>
                            <Text style={styles.resultItemName}>{item.name}</Text>
                            <View style={styles.quantityContainer}>
                              <TouchableOpacity
                                style={styles.quantityButton}
                                onPress={() => {
                                  const currentQty = itemQuantities.get(itemKey) || item.quantity || 1;
                                  if (currentQty > 1) {
                                    const newQuantities = new Map(itemQuantities);
                                    newQuantities.set(itemKey, currentQty - 1);
                                    setItemQuantities(newQuantities);
                                  }
                                }}
                              >
                                <Ionicons name="remove" size={16} color="#2196F3" />
                              </TouchableOpacity>
                              <TextInput
                                style={styles.quantityInput}
                                value={String(itemQuantities.get(itemKey) || item.quantity || 1)}
                                onChangeText={(text: string) => {
                                  const num = parseInt(text) || 1;
                                  const newQuantities = new Map(itemQuantities);
                                  newQuantities.set(itemKey, Math.max(1, num));
                                  setItemQuantities(newQuantities);
                                }}
                                keyboardType="numeric"
                                selectTextOnFocus
                              />
                              <TouchableOpacity
                                style={styles.quantityButton}
                                onPress={() => {
                                  const currentQty = itemQuantities.get(itemKey) || item.quantity || 1;
                                  const newQuantities = new Map(itemQuantities);
                                  newQuantities.set(itemKey, currentQty + 1);
                                  setItemQuantities(newQuantities);
                                }}
                              >
                                <Ionicons name="add" size={16} color="#2196F3" />
                              </TouchableOpacity>
                            </View>
                          </View>
                          <Text style={styles.resultItemCategory}>{item.category}</Text>
                        </View>
                        <View style={styles.resultItemRight}>
                          {item.confidence_score !== undefined && (
                            <Text style={styles.confidenceText}>
                              {`${Math.round(item.confidence_score * 100)}%`}
                            </Text>
                          )}
                        </View>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>
            )}

            {/* Model 2 Results */}
            {detectionResults.model2_results && detectionResults.model2_results.length > 0 && (
              <View style={styles.modelSection}>
                <View style={styles.modelHeader}>
                  <Text style={styles.modelTitle}>Model 2 ({detectionResults.model2_results.length})</Text>
                </View>
                {detectionResults.model2_results.map((item, index) => {
                  const itemKey = item.id || `model2-${index}`;
                  const isSelected = selectedItems.has(itemKey);
                  return (
                    <TouchableOpacity
                      key={itemKey}
                      style={[
                        styles.resultItem,
                        isSelected && styles.resultItemSelected,
                      ]}
                      onPress={() => toggleItemSelection(itemKey)}
                      activeOpacity={0.7}
                    >
                      <View style={styles.resultItemCheckbox}>
                        <Ionicons
                          name={isSelected ? 'checkbox' : 'checkbox-outline'}
                          size={24}
                          color={isSelected ? '#2196F3' : '#BDC3C7'}
                        />
                      </View>
                      <View style={styles.resultItemContent}>
                        <View style={styles.resultItemLeft}>
                          <View style={styles.itemNameRow}>
                            <Text style={styles.resultItemName}>{item.name}</Text>
                            <View style={styles.quantityContainer}>
                              <TouchableOpacity
                                style={styles.quantityButton}
                                onPress={() => {
                                  const currentQty = itemQuantities.get(itemKey) || item.quantity || 1;
                                  if (currentQty > 1) {
                                    const newQuantities = new Map(itemQuantities);
                                    newQuantities.set(itemKey, currentQty - 1);
                                    setItemQuantities(newQuantities);
                                  }
                                }}
                              >
                                <Ionicons name="remove" size={16} color="#2196F3" />
                              </TouchableOpacity>
                              <TextInput
                                style={styles.quantityInput}
                                value={String(itemQuantities.get(itemKey) || item.quantity || 1)}
                                onChangeText={(text: string) => {
                                  const num = parseInt(text) || 1;
                                  const newQuantities = new Map(itemQuantities);
                                  newQuantities.set(itemKey, Math.max(1, num));
                                  setItemQuantities(newQuantities);
                                }}
                                keyboardType="numeric"
                                selectTextOnFocus
                              />
                              <TouchableOpacity
                                style={styles.quantityButton}
                                onPress={() => {
                                  const currentQty = itemQuantities.get(itemKey) || item.quantity || 1;
                                  const newQuantities = new Map(itemQuantities);
                                  newQuantities.set(itemKey, currentQty + 1);
                                  setItemQuantities(newQuantities);
                                }}
                              >
                                <Ionicons name="add" size={16} color="#2196F3" />
                              </TouchableOpacity>
                            </View>
                          </View>
                          <Text style={styles.resultItemCategory}>{item.category}</Text>
                        </View>
                        <View style={styles.resultItemRight}>
                          {item.confidence_score !== undefined && (
                            <Text style={styles.confidenceText}>
                              {`${Math.round(item.confidence_score * 100)}%`}
                            </Text>
                          )}
                        </View>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>
            )}

            {/* Select All / Deselect All */}
            {(detectionResults.model1_results?.length || 0) + (detectionResults.model2_results?.length || 0) > 0 && (
              <View style={styles.selectAllContainer}>
                {selectedItems.size > 0 ? (
                  <TouchableOpacity
                    style={styles.selectAllButton}
                    onPress={deselectAllItems}
                  >
                    <Text style={styles.selectAllText}>Deselect All</Text>
                  </TouchableOpacity>
                ) : (
                  <TouchableOpacity
                    style={styles.selectAllButton}
                    onPress={() => {
                      const allItems = [
                        ...(detectionResults.model1_results || []).map((item) => item.id || `model1-${Date.now()}`),
                        ...(detectionResults.model2_results || []).map((item) => item.id || `model2-${Date.now()}`),
                      ];
                      setSelectedItems(new Set(allItems));
                    }}
                  >
                    <Text style={styles.selectAllText}>Select All</Text>
                  </TouchableOpacity>
                )}
              </View>
            )}

            {/* Add to Pantry Button */}
            {selectedItems.size > 0 && (
              <TouchableOpacity
                style={[
                  styles.addToPantryButton,
                  addingToPantry && styles.addToPantryButtonDisabled,
                ]}
                onPress={addSelectedToPantry}
                disabled={addingToPantry}
              >
                {addingToPantry ? (
                  <ActivityIndicator color="white" />
                ) : (
                  <>
                    <Ionicons name="basket" size={20} color="white" />
                    <Text style={styles.addToPantryButtonText}>
                      Add {selectedItems.size} Item{selectedItems.size > 1 ? 's' : ''} to Pantry
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Instructions */}
        <View style={styles.instructionsContainer}>
          <Text style={styles.instructionsTitle}>Tips for Best Results:</Text>
          <Text style={styles.instructionItem}>• Ensure good lighting</Text>
          <Text style={styles.instructionItem}>• Avoid glare and shadows</Text>
          <Text style={styles.instructionItem}>• Capture entire fridge view</Text>
          <Text style={styles.instructionItem}>• Keep camera steady</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  header: {
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#7F8C8D',
    lineHeight: 20,
  },
  imageContainer: {
    position: 'relative',
    width: '100%',
    height: 300,
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 20,
    backgroundColor: '#ECF0F1',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  previewImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  clearButton: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 15,
    padding: 5,
  },
  placeholderContainer: {
    width: '100%',
    height: 300,
    borderRadius: 12,
    backgroundColor: '#ECF0F1',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    borderWidth: 2,
    borderColor: '#BDC3C7',
    borderStyle: 'dashed',
  },
  placeholderText: {
    marginTop: 12,
    fontSize: 16,
    color: '#7F8C8D',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
    gap: 12,
  },
  button: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  galleryButton: {
    backgroundColor: '#3498DB',
  },
  cameraButton: {
    backgroundColor: '#27AE60',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  scanButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#2196F3',
    padding: 18,
    borderRadius: 12,
    marginBottom: 24,
    gap: 10,
  },
  scanButtonDisabled: {
    opacity: 0.6,
  },
  scanButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  resultsContainer: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
  },
  resultsTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 16,
  },
  modelSection: {
    marginBottom: 20,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#ECF0F1',
  },
  modelHeader: {
    marginBottom: 12,
  },
  modelTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#2196F3',
    marginBottom: 8,
  },
  selectAllContainer: {
    alignItems: 'center',
    marginTop: 10,
    marginBottom: 10,
  },
  selectAllButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  selectAllText: {
    fontSize: 14,
    color: '#2196F3',
    fontWeight: '600',
  },
  resultItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#ECF0F1',
    borderRadius: 8,
    marginBottom: 4,
  },
  resultItemSelected: {
    backgroundColor: '#E3F2FD',
    borderWidth: 1,
    borderColor: '#2196F3',
  },
  resultItemCheckbox: {
    marginRight: 12,
  },
  resultItemContent: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  resultItemLeft: {
    flex: 1,
  },
  itemNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  resultItemName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2C3E50',
    textTransform: 'capitalize',
    flex: 1,
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    padding: 4,
    marginLeft: 10,
  },
  quantityButton: {
    padding: 4,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quantityInput: {
    minWidth: 40,
    textAlign: 'center',
    fontSize: 14,
    fontWeight: '600',
    color: '#2C3E50',
    paddingHorizontal: 8,
  },
  resultItemCategory: {
    fontSize: 14,
    color: '#7F8C8D',
    textTransform: 'capitalize',
  },
  resultItemRight: {
    alignItems: 'flex-end',
    marginLeft: 10,
  },
  confidenceText: {
    fontSize: 12,
    color: '#7F8C8D',
    fontWeight: '500',
  },
  addToPantryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
    marginTop: 16,
    gap: 8,
  },
  addToPantryButtonDisabled: {
    opacity: 0.6,
  },
  addToPantryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  instructionsContainer: {
    backgroundColor: '#EBF5FB',
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
  },
  instructionsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2C3E50',
    marginBottom: 12,
  },
  instructionItem: {
    fontSize: 14,
    color: '#34495E',
    marginBottom: 6,
    lineHeight: 20,
  },
});

export default ScannerScreen;
