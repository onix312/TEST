// Install in Assets/Editor via GameDev AI Office. This file never depends on runtime packages.
#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace GameDevAIOffice
{
    [Serializable]
    public class SceneSpec
    {
        public string name = "AIOfficeScene";
        public SceneObjectSpec[] objects;
    }

    [Serializable]
    public class SceneObjectSpec
    {
        public string name = "Object";
        public string primitive = "";
        public float[] position;
        public float[] rotation;
        public float[] scale;
    }

    [Serializable]
    public class SceneReport
    {
        public string scene;
        public string[] objects;
        public string[] enabledBuildScenes;
    }

    public static class EditorBridge
    {
        private static string OfficeFolder
        {
            get { return Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".ai-office")); }
        }

        [MenuItem("Tools/GameDev AI Office/Generate Scene From Spec")]
        public static void CreateSceneFromSpec()
        {
            var specPath = Path.Combine(OfficeFolder, "scene-spec.json");
            if (!File.Exists(specPath))
            {
                Debug.LogError("GameDev AI Office: create .ai-office/scene-spec.json before generating a scene.");
                return;
            }
            var config = JsonUtility.FromJson<SceneSpec>(File.ReadAllText(specPath));
            if (config == null) throw new InvalidOperationException("Invalid scene specification.");
            var name = string.IsNullOrWhiteSpace(config.name) ? "AIOfficeScene" : config.name;
            foreach (var forbidden in Path.GetInvalidFileNameChars())
                name = name.Replace(forbidden, '_');

            var location = "Assets/Scenes";
            Directory.CreateDirectory(Path.Combine(Application.dataPath, "Scenes"));
            var scenePath = AssetDatabase.GenerateUniqueAssetPath(location + "/" + name + ".unity");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            if (config.objects != null)
            {
                foreach (var item in config.objects)
                {
                    if (item == null) continue;
                    GameObject obj;
                    PrimitiveType type;
                    if (!string.IsNullOrWhiteSpace(item.primitive)
                        && Enum.TryParse(item.primitive, true, out type)
                        && Enum.IsDefined(typeof(PrimitiveType), type))
                        obj = GameObject.CreatePrimitive(type);
                    else
                        obj = new GameObject();
                    obj.name = string.IsNullOrWhiteSpace(item.name) ? "Object" : item.name;
                    if (item.position != null && item.position.Length == 3)
                        obj.transform.position = new Vector3(item.position[0], item.position[1], item.position[2]);
                    if (item.rotation != null && item.rotation.Length == 3)
                        obj.transform.eulerAngles = new Vector3(item.rotation[0], item.rotation[1], item.rotation[2]);
                    if (item.scale != null && item.scale.Length == 3)
                        obj.transform.localScale = new Vector3(item.scale[0], item.scale[1], item.scale[2]);
                }
            }
            EditorSceneManager.SaveScene(scene, scenePath);
            AssetDatabase.Refresh();
            Debug.Log("GameDev AI Office: scene saved at " + scenePath);
        }

        [MenuItem("Tools/GameDev AI Office/Export Scene Report")]
        public static void ExportSceneReport()
        {
            Directory.CreateDirectory(Path.Combine(OfficeFolder, "reports"));
            Scene active = SceneManager.GetActiveScene();
            var objectNames = new List<string>();
            foreach (var obj in active.GetRootGameObjects())
                objectNames.Add(obj.name);
            var buildScenes = new List<string>();
            foreach (var scene in EditorBuildSettings.scenes)
                if (scene.enabled) buildScenes.Add(scene.path);
            var report = new SceneReport {
                scene = active.path,
                objects = objectNames.ToArray(),
                enabledBuildScenes = buildScenes.ToArray()
            };
            File.WriteAllText(Path.Combine(OfficeFolder, "reports", "scene.json"),
                              JsonUtility.ToJson(report, true));
            Debug.Log("GameDev AI Office: scene report exported");
        }

        [MenuItem("Tools/GameDev AI Office/Build Windows")]
        public static void BuildWindows()
        {
            var scenes = new List<string>();
            foreach (var item in EditorBuildSettings.scenes)
                if (item.enabled) scenes.Add(item.path);
            if (scenes.Count == 0)
                throw new InvalidOperationException("Add scenes to File > Build Settings before building.");

            var output = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Builds", "GameDevAI"));
            Directory.CreateDirectory(output);
            var options = new BuildPlayerOptions {
                scenes = scenes.ToArray(),
                locationPathName = Path.Combine(output, "Game.exe"),
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None
            };
            var result = BuildPipeline.BuildPlayer(options);
            if (result.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
                throw new Exception("GameDev AI Office: build failed: " + result.summary.result);
            Debug.Log("GameDev AI Office: build completed at " + output);
        }
    }
}
#endif
