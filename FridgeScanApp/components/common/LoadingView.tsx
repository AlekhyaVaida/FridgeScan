// Shared loading component

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface LoadingViewProps {
  message?: string;
}

const LoadingView: React.FC<LoadingViewProps> = ({ message = 'Loading...' }) => {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>{message}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
  },
  text: {
    fontSize: 16,
    color: '#666',
  },
});

export default LoadingView;

