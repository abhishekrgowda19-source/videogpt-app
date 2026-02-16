import React, { useState, useEffect } from "react";
import { View, Text, Button, StyleSheet, Alert, ActivityIndicator } from "react-native";
import * as ImagePicker from "expo-image-picker";
import axios from "axios";

export default function App() {

  const [file, setFile] = useState<any>(null);
  const [result, setResult] = useState("No result yet");
  const [loading, setLoading] = useState(false);

  // ✅ YOUR PERMANENT RENDER BACKEND
  const SERVER_URL = "https://videogpt-app.onrender.com/process";

  // ================= PERMISSION =================

  useEffect(() => {

    (async () => {

      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();

      if (!permission.granted) {
        Alert.alert(
          "Permission required",
          "Please allow gallery access"
        );
      }

    })();

  }, []);

  // ================= PICK VIDEO =================

  const pickVideo = async () => {

    try {

      const res = await ImagePicker.launchImageLibraryAsync({

        mediaTypes: ImagePicker.MediaTypeOptions.Videos,
        allowsEditing: false,
        quality: 1,

      });

      if (!res.canceled) {

        setFile(res.assets[0]);

        Alert.alert("Video Selected");

        console.log("Video URI:", res.assets[0].uri);

      }

    } catch (error) {

      console.log(error);
      Alert.alert("Video selection failed");

    }

  };

  // ================= UPLOAD VIDEO =================

  const uploadVideo = async () => {

    if (!file) {

      Alert.alert("Select video first");
      return;

    }

    try {

      setLoading(true);
      setResult("Uploading and analyzing...");

      const formData = new FormData();

      formData.append("file", {

        uri: file.uri,
        name: file.fileName || "video.mp4",
        type: file.mimeType || "video/mp4",

      } as any);

      const response = await axios({

        method: "POST",
        url: SERVER_URL,
        data: formData,

        headers: {
          "Content-Type": "multipart/form-data",
        },

        timeout: 600000, // 10 min

      });

      console.log("Server response:", response.data);

      if (response.data && response.data.content_summary) {

        setResult(response.data.content_summary);

      } else {

        setResult("No result returned");

      }

    } catch (error: any) {

      console.log("UPLOAD ERROR:", error);

      if (error.response) {

        setResult("Server error");

      } else if (error.request) {

        setResult("Cannot reach backend");

      } else {

        setResult("Upload failed");

      }

    } finally {

      setLoading(false);

    }

  };

  // ================= UI =================

  return (

    <View style={styles.container}>

      <Text style={styles.title}>VideoGPT Mobile</Text>

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
        <ActivityIndicator size="large" color="blue" />
      )}

      <Text style={styles.result}>
        {result}
      </Text>

    </View>

  );

}

// ================= STYLE =================

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
    marginBottom: 25,

  },

  result: {

    marginTop: 20,
    fontSize: 18,
    textAlign: "center",

  },

});
