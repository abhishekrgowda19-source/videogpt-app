import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Button,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Platform
} from "react-native";

import * as ImagePicker from "expo-image-picker";
import axios from "axios";

export default function App() {

  const [file, setFile] = useState<any>(null);
  const [result, setResult] = useState("No result yet");
  const [loading, setLoading] = useState(false);

  // ✅ YOUR RENDER BACKEND
  const SERVER_URL = "https://videogpt-app.onrender.com/process";

  // ================= PERMISSION =================

  useEffect(() => {

    (async () => {

      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permission.granted) {
        Alert.alert("Permission required");
      }

    })();

  }, []);

  // ================= PICK VIDEO =================

  const pickVideo = async () => {

    try {

      const res = await ImagePicker.launchImageLibraryAsync({

        mediaTypes: ImagePicker.MediaTypeOptions.Videos,
        allowsEditing: false,
        quality: 0.5, // ✅ IMPORTANT reduce size

      });

      if (!res.canceled) {

        setFile(res.assets[0]);

        Alert.alert("Video selected");

        console.log(res.assets[0]);

      }

    } catch (e) {

      Alert.alert("Selection failed");

    }

  };

  // ================= UPLOAD =================

  const uploadVideo = async () => {

    if (!file) {

      Alert.alert("Select video first");
      return;

    }

    try {

      setLoading(true);
      setResult("Uploading...");

      const formData = new FormData();

      formData.append("file", {

        uri:
          Platform.OS === "android"
            ? file.uri
            : file.uri.replace("file://", ""),

        name: "video.mp4",

        type: "video/mp4",

      } as any);

      console.log("Uploading...");

      const response = await axios.post(

        SERVER_URL,
        formData,

        {
          headers: {
            "Content-Type": "multipart/form-data",
          },

          timeout: 300000, // 5 min max

        }

      );

      console.log("Response:", response.data);

      if (response.data.content_summary) {

        setResult(response.data.content_summary);

      } else {

        setResult("No result returned");

      }

    } catch (error: any) {

      console.log(error);

      if (error.response) {

        console.log(error.response.data);

        setResult("Server error");

      }

      else if (error.request) {

        setResult("Server not reachable");

      }

      else {

        setResult("Upload failed");

      }

    }

    finally {

      setLoading(false);

    }

  };

  // ================= UI =================

  return (

    <View style={styles.container}>

      <Text style={styles.title}>
        VideoGPT Mobile
      </Text>

      <Button
        title="Select Video"
        onPress={pickVideo}
      />

      <View style={{ height: 15 }} />

      <Button
        title="Upload and Analyze"
        onPress={uploadVideo}
      />

      <View style={{ height: 20 }} />

      {loading && (
        <ActivityIndicator size="large" />
      )}

      <Text style={styles.result}>
        {result}
      </Text>

    </View>

  );

}

const styles = StyleSheet.create({

  container: {

    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,

  },

  title: {

    fontSize: 26,
    fontWeight: "bold",
    marginBottom: 20,

  },

  result: {

    marginTop: 20,
    fontSize: 18,
    textAlign: "center",

  },

});
