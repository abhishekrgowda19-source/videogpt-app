import React, { useState, useEffect } from "react";
import { View, Text, Button, StyleSheet, Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import axios from "axios";

export default function App() {

  const [file, setFile] = useState<any>(null);
  const [result, setResult] = useState("No result yet");

 const SERVER_URL = "https://diplostemonous-feedable-felix.ngrok-free.dev/process";


  useEffect(() => {
    (async () => {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert("Permission required");
      }
    })();
  }, []);

  const pickVideo = async () => {

    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Videos,
    });

    if (!res.canceled) {
      setFile(res.assets[0]);
    }

  };

  const uploadVideo = async () => {

    if (!file) {
      Alert.alert("Select video first");
      return;
    }

    const formData = new FormData();

    formData.append("file", {
      uri: file.uri,
      name: "video.mp4",
      type: "video/mp4",
    } as any);

    try {

      setResult("Uploading...");

      const response = await axios.post(
        SERVER_URL,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setResult(response.data.content_summary);

    } catch (error) {

      console.log(error);
      setResult("Error processing video");

    }

  };

  return (

    <View style={styles.container}>

      <Text style={styles.title}>VideoGPT Mobile</Text>

      <Button title="Select Video" onPress={pickVideo} />

      <View style={{ height: 10 }} />

      <Button title="Upload and Analyze" onPress={uploadVideo} />

      <Text style={styles.result}>{result}</Text>

    </View>

  );

}

const styles = StyleSheet.create({

  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  title: {
    fontSize: 24,
    marginBottom: 20,
  },

  result: {
    marginTop: 20,
    fontSize: 18,
    textAlign: "center",
  },

});
