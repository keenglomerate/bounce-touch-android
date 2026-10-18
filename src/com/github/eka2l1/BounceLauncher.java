package com.github.eka2l1;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public class BounceLauncher extends Activity {
    private static final int PERMISSION_REQ_CODE = 1001;
    private TextView statusText;
    private ProgressBar progressBar;
    private Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER);
        layout.setBackgroundColor(Color.rgb(18, 18, 18));
        layout.setPadding(40, 40, 40, 40);

        TextView title = new TextView(this);
        title.setText("BOUNCE TOUCH");
        title.setTextColor(Color.rgb(255, 60, 60));
        title.setTextSize(26);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        title.setGravity(Gravity.CENTER);
        layout.addView(title);

        progressBar = new ProgressBar(this);
        progressBar.setVisibility(View.GONE);
        LinearLayout.LayoutParams pParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        pParams.setMargins(0, 30, 0, 20);
        layout.addView(progressBar, pParams);

        statusText = new TextView(this);
        statusText.setText("Starting Bounce Touch...");
        statusText.setTextColor(Color.rgb(200, 200, 200));
        statusText.setTextSize(14);
        statusText.setGravity(Gravity.CENTER);
        layout.addView(statusText);

        setContentView(layout);

        checkAndProceed();
    }

    private File getStorageDir() {
        if (Build.VERSION.SDK_INT >= 29 && !Environment.isExternalStorageLegacy()) {
            File ext = getExternalFilesDir(null);
            if (ext != null) {
                return ext;
            }
        }
        return new File(Environment.getExternalStorageDirectory(), "EKA2L1");
    }

    private void checkAndProceed() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && Build.VERSION.SDK_INT < 30) {
            if (Environment.isExternalStorageLegacy() &&
                    checkSelfPermission("android.permission.WRITE_EXTERNAL_STORAGE")
                    != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                        "android.permission.WRITE_EXTERNAL_STORAGE",
                        "android.permission.READ_EXTERNAL_STORAGE"
                }, PERMISSION_REQ_CODE);
                return;
            }
        }
        startSetupOrLaunch();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQ_CODE) {
            startSetupOrLaunch();
        }
    }

    private void startSetupOrLaunch() {
        File storageDir = getStorageDir();
        File bounceExe = new File(storageDir, "data/drives/e/sys/bin/Bounce.exe");
        File legacyExe = new File(Environment.getExternalStorageDirectory(), "EKA2L1/data/drives/e/sys/bin/Bounce.exe");
        if (bounceExe.exists() || legacyExe.exists()) {
            launchGame();
        } else {
            progressBar.setVisibility(View.VISIBLE);
            statusText.setText("Extracting Bounce Touch assets (first run only)...");
            new Thread(new Runnable() {
                @Override
                public void run() {
                    boolean ok = extractDataZip(storageDir);
                    mainHandler.post(new Runnable() {
                        @Override
                        public void run() {
                            if (ok) {
                                launchGame();
                            } else {
                                statusText.setText("Failed to extract game data. Please check storage.");
                            }
                        }
                    });
                }
            }).start();
        }
    }

    private boolean extractDataZip(File targetDir) {
        if (!targetDir.exists()) {
            targetDir.mkdirs();
        }
        try {
            InputStream is = getAssets().open("data.zip");
            ZipInputStream zis = new ZipInputStream(is);
            ZipEntry entry;
            byte[] buffer = new byte[65536];
            while ((entry = zis.getNextEntry()) != null) {
                File file = new File(targetDir, entry.getName());
                if (entry.isDirectory()) {
                    file.mkdirs();
                } else {
                    File parent = file.getParentFile();
                    if (parent != null && !parent.exists()) {
                        parent.mkdirs();
                    }
                    FileOutputStream fos = new FileOutputStream(file);
                    int count;
                    while ((count = zis.read(buffer)) != -1) {
                        fos.write(buffer, 0, count);
                    }
                    fos.close();
                }
                zis.closeEntry();
            }
            zis.close();
            is.close();
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    private void ensureGameConfig() {
        String cfgContent = "{\n" +
                "  \"Version\": 1,\n" +
                "  \"ScreenBackgroundColor\": 0,\n" +
                "  \"ScreenBackgroundImageOpacity\": 0,\n" +
                "  \"ScreenBackgroundImageKeepAspectRatio\": true,\n" +
                "  \"ScreenScaleRatio\": 100,\n" +
                "  \"Orientation\": 3,\n" +
                "  \"ScreenScaleType\": 1,\n" +
                "  \"ScreenGravity\": 2,\n" +
                "  \"ScreenShowNotch\": true,\n" +
                "  \"TouchInput\": true,\n" +
                "  \"ShowKeyboard\": false,\n" +
                "  \"VirtualKeyboardType\": 0,\n" +
                "  \"VirtualKeyboardShowEditKey\": false,\n" +
                "  \"ButtonShape\": 2,\n" +
                "  \"VirtualKeyboardAlpha\": 0,\n" +
                "  \"VirtualKeyboardFeedback\": false,\n" +
                "  \"VirtualKeyboardDelay\": 0,\n" +
                "  \"VirtualKeyboardColorBackground\": 0,\n" +
                "  \"VirtualKeyboardColorBackgroundSelected\": 128,\n" +
                "  \"VirtualKeyboardColorForeground\": 128,\n" +
                "  \"VirtualKeyboardColorForegroundSelected\": 16777215,\n" +
                "  \"VirtualKeyboardColorOutline\": 16777215,\n" +
                "  \"b\": 1,\n" +
                "  \"c\": 0,\n" +
                "  \"d\": 0,\n" +
                "  \"e\": true,\n" +
                "  \"f\": 100,\n" +
                "  \"g\": 3,\n" +
                "  \"h\": 1,\n" +
                "  \"i\": 2,\n" +
                "  \"j\": true,\n" +
                "  \"k\": true,\n" +
                "  \"l\": false\n" +
                "}";

        File[] dirs = new File[] {
                new File(getStorageDir(), "android/configs/2000C4D4"),
                new File(Environment.getExternalStorageDirectory(), "EKA2L1/android/configs/2000C4D4")
        };

        for (File cfgDir : dirs) {
            try {
                if (!cfgDir.exists()) {
                    cfgDir.mkdirs();
                }
                File cfgFile = new File(cfgDir, "config.json");
                FileOutputStream fos = new FileOutputStream(cfgFile);
                fos.write(cfgContent.getBytes("UTF-8"));
                fos.close();
            } catch (Exception ignored) {
            }
        }
    }

    private void launchGame() {
        ensureGameConfig();
        statusText.setText("Launching...");
        try {
            Intent intent = new Intent();
            intent.setClassName(this, "com.github.eka2l1.emu.EmulatorActivity");
            intent.putExtra("appUid", 536921300L);
            intent.putExtra("appName", "Bounce Touch");
            intent.putExtra("appDeviceCode", "RM-356");
            intent.putExtra("appIsShortcut", true);
            startActivity(intent);
            finish();
        } catch (Exception e) {
            e.printStackTrace();
            statusText.setText("Error launching Bounce Touch: " + e.getMessage());
        }
    }
}
