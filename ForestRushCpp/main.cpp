#include "raylib.h"
#include <cmath>
#include <cstdlib>
#include <cstdio>

// Forest Rush C++ — original lane-based endless runner.
// Designed for portrait Android. No external art is required: the entire scene
// is built from smooth 3D geometry so the runner is rounded, not blocky.

static constexpr int LANES = 3;
static constexpr float LANE_X[LANES] = {-2.35f, 0.0f, 2.35f};
static constexpr float PLAYER_Z = 2.0f;
static constexpr int OBSTACLE_COUNT = 28;
static constexpr int COIN_COUNT = 64;
static constexpr int TREE_COUNT = 56;
static constexpr int ROAD_SEGMENTS = 9;
static constexpr float SEGMENT_LEN = 24.0f;
static constexpr float WORLD_SPAN = ROAD_SEGMENTS * SEGMENT_LEN;

struct Obstacle {
    float x, z;
    int lane;
    int type; // 0 rock, 1 log, 2 low branch, 3 stump
    bool active;
};

struct Coin {
    float x, z, y;
    int lane;
    bool active;
    float phase;
};

struct Tree {
    float x, z, scale;
    int variant;
};

enum class ScreenState { Menu, Playing, Paused, GameOver };

static ScreenState state = ScreenState::Menu;
static Obstacle obstacles[OBSTACLE_COUNT]{};
static Coin coins[COIN_COUNT]{};
static Tree trees[TREE_COUNT]{};

static int targetLane = 1;
static float playerX = 0.0f;
static float jumpY = 0.0f;
static float jumpV = 0.0f;
static float slideTimer = 0.0f;
static float runTime = 0.0f;
static float distanceRun = 0.0f;
static float speed = 13.5f;
static int coinScore = 0;
static int bestScore = 0;
static bool touchHeld = false;
static Vector2 touchStart{};
static float hitFlash = 0.0f;

static float RandF(float a, float b) {
    return a + (b-a) * ((float)GetRandomValue(0, 10000) / 10000.0f);
}

static Color Mix(Color a, Color b, float t) {
    if (t < 0) t = 0; if (t > 1) t = 1;
    return Color{
        (unsigned char)(a.r + (b.r-a.r)*t),
        (unsigned char)(a.g + (b.g-a.g)*t),
        (unsigned char)(a.b + (b.b-a.b)*t),
        (unsigned char)(a.a + (b.a-a.a)*t)
    };
}

static void ResetWorld() {
    targetLane = 1;
    playerX = 0;
    jumpY = jumpV = 0;
    slideTimer = 0;
    runTime = 0;
    distanceRun = 0;
    speed = 13.5f;
    coinScore = 0;
    hitFlash = 0;

    for (int i=0;i<OBSTACLE_COUNT;i++) {
        obstacles[i].lane = GetRandomValue(0,2);
        obstacles[i].x = LANE_X[obstacles[i].lane];
        obstacles[i].z = -14.0f - i*6.9f - RandF(0,3.2f);
        obstacles[i].type = GetRandomValue(0,3);
        obstacles[i].active = true;
    }
    for (int i=0;i<COIN_COUNT;i++) {
        coins[i].lane = GetRandomValue(0,2);
        coins[i].x = LANE_X[coins[i].lane];
        coins[i].z = -7.0f - i*3.0f - RandF(0,1.8f);
        coins[i].y = (GetRandomValue(0,5)==0)? 1.25f : 0.82f;
        coins[i].active = true;
        coins[i].phase = RandF(0,6.28f);
    }
    for (int i=0;i<TREE_COUNT;i++) {
        float side = (i%2==0)? -1.0f : 1.0f;
        trees[i].x = side * RandF(5.1f, 10.8f);
        trees[i].z = -RandF(1.0f, WORLD_SPAN);
        trees[i].scale = RandF(0.72f, 1.38f);
        trees[i].variant = GetRandomValue(0,2);
    }
}

static void MoveLane(int delta) {
    targetLane += delta;
    if (targetLane < 0) targetLane = 0;
    if (targetLane > 2) targetLane = 2;
}

static void Jump() {
    if (jumpY <= 0.001f && slideTimer <= 0.0f) jumpV = 8.3f;
}

static void Slide() {
    if (jumpY <= 0.15f) slideTimer = 0.72f;
}

static void HandleInput() {
    if (IsKeyPressed(KEY_LEFT) || IsKeyPressed(KEY_A)) MoveLane(-1);
    if (IsKeyPressed(KEY_RIGHT) || IsKeyPressed(KEY_D)) MoveLane(1);
    if (IsKeyPressed(KEY_UP) || IsKeyPressed(KEY_W) || IsKeyPressed(KEY_SPACE)) Jump();
    if (IsKeyPressed(KEY_DOWN) || IsKeyPressed(KEY_S)) Slide();

    int gestures = GetGestureDetected();
    if (gestures & GESTURE_SWIPE_LEFT) MoveLane(-1);
    if (gestures & GESTURE_SWIPE_RIGHT) MoveLane(1);
    if (gestures & GESTURE_SWIPE_UP) Jump();
    if (gestures & GESTURE_SWIPE_DOWN) Slide();

    if (GetTouchPointCount() > 0) {
        Vector2 p = GetTouchPosition(0);
        if (!touchHeld) { touchHeld = true; touchStart = p; }
    } else if (touchHeld) {
        Vector2 end = GetMousePosition();
        Vector2 d{end.x-touchStart.x, end.y-touchStart.y};
        if (fabsf(d.x) > 55 || fabsf(d.y) > 55) {
            if (fabsf(d.x) > fabsf(d.y)) MoveLane(d.x < 0 ? -1 : 1);
            else if (d.y < 0) Jump(); else Slide();
        }
        touchHeld = false;
    }
}

static void DrawShadow(Vector3 p, float r, float alpha) {
    DrawCircle3D(Vector3{p.x, 0.025f, p.z}, r, Vector3{1,0,0}, 90.0f, Color{15,25,20,(unsigned char)(alpha*255)});
}

static void DrawRoundedLimb(Vector3 a, Vector3 b, float radius, Color c) {
    DrawCapsule(a,b,radius,8,3,c);
}

static void DrawRunner(float t) {
    float bob = sinf(t*11.0f)*0.045f;
    float swing = sinf(t*11.0f) * 0.34f;
    float y = 0.20f + jumpY + bob;
    bool sliding = slideTimer > 0;
    float bodyTilt = sliding ? 0.62f : 0.0f;
    float bodyY = sliding ? y+0.82f : y+1.42f;

    DrawShadow(Vector3{playerX,0,PLAYER_Z}, sliding?0.52f:0.44f, jumpY>0.6f?0.10f:0.22f);

    Color skin{234,174,120,255};
    Color shirt{40,93,127,255};
    Color shirt2{29,70,96,255};
    Color pants{41,47,63,255};
    Color shoes{232,219,190,255};
    Color hair{47,31,25,255};
    Color pack{186,76,50,255};

    if (sliding) {
        DrawRoundedLimb(Vector3{playerX-0.20f,y+0.36f,PLAYER_Z+0.05f}, Vector3{playerX-0.28f,y+0.22f,PLAYER_Z+0.72f},0.15f,pants);
        DrawRoundedLimb(Vector3{playerX+0.20f,y+0.36f,PLAYER_Z+0.05f}, Vector3{playerX+0.31f,y+0.20f,PLAYER_Z-0.45f},0.15f,pants);
        DrawCapsule(Vector3{playerX,bodyY-0.26f,PLAYER_Z+bodyTilt*0.18f}, Vector3{playerX,bodyY+0.40f,PLAYER_Z-bodyTilt*0.38f},0.40f,10,4,shirt);
        DrawSphere(Vector3{playerX,bodyY+0.67f,PLAYER_Z-bodyTilt*0.64f},0.34f,skin);
        DrawSphere(Vector3{playerX,bodyY+0.79f,PLAYER_Z-bodyTilt*0.66f+0.05f},0.31f,hair);
    } else {
        float lz = swing, rz = -swing;
        Vector3 hipL{playerX-0.20f,y+1.02f,PLAYER_Z};
        Vector3 hipR{playerX+0.20f,y+1.02f,PLAYER_Z};
        Vector3 kneeL{playerX-0.21f,y+0.58f,PLAYER_Z+lz};
        Vector3 kneeR{playerX+0.21f,y+0.58f,PLAYER_Z+rz};
        Vector3 footL{playerX-0.22f,y+0.13f,PLAYER_Z-lz*0.42f};
        Vector3 footR{playerX+0.22f,y+0.13f,PLAYER_Z-rz*0.42f};
        DrawRoundedLimb(hipL,kneeL,0.16f,pants); DrawRoundedLimb(kneeL,footL,0.14f,pants);
        DrawRoundedLimb(hipR,kneeR,0.16f,pants); DrawRoundedLimb(kneeR,footR,0.14f,pants);
        DrawRoundedLimb(Vector3{footL.x,footL.y,footL.z+0.10f},Vector3{footL.x,footL.y,footL.z-0.30f},0.14f,shoes);
        DrawRoundedLimb(Vector3{footR.x,footR.y,footR.z+0.10f},Vector3{footR.x,footR.y,footR.z-0.30f},0.14f,shoes);

        DrawCapsule(Vector3{playerX,y+1.10f,PLAYER_Z},Vector3{playerX,y+1.92f,PLAYER_Z-0.02f},0.42f,10,4,shirt);
        DrawSphere(Vector3{playerX,y+1.79f,PLAYER_Z-0.01f},0.45f,shirt);
        DrawCapsule(Vector3{playerX,y+1.86f,PLAYER_Z-0.01f},Vector3{playerX,y+2.10f,PLAYER_Z-0.02f},0.16f,8,3,skin);

        Vector3 shL{playerX-0.47f,y+1.80f,PLAYER_Z};
        Vector3 shR{playerX+0.47f,y+1.80f,PLAYER_Z};
        Vector3 handL{playerX-0.54f,y+1.05f,PLAYER_Z-swing*0.95f};
        Vector3 handR{playerX+0.54f,y+1.05f,PLAYER_Z+swing*0.95f};
        DrawRoundedLimb(shL,handL,0.13f,shirt2); DrawSphere(handL,0.15f,skin);
        DrawRoundedLimb(shR,handR,0.13f,shirt2); DrawSphere(handR,0.15f,skin);

        DrawCapsule(Vector3{playerX,y+1.28f,PLAYER_Z+0.32f},Vector3{playerX,y+1.78f,PLAYER_Z+0.34f},0.30f,10,4,pack);
        DrawRoundedLimb(Vector3{playerX-0.31f,y+1.72f,PLAYER_Z+0.14f},Vector3{playerX-0.30f,y+1.25f,PLAYER_Z+0.16f},0.055f,Color{112,50,38,255});
        DrawRoundedLimb(Vector3{playerX+0.31f,y+1.72f,PLAYER_Z+0.14f},Vector3{playerX+0.30f,y+1.25f,PLAYER_Z+0.16f},0.055f,Color{112,50,38,255});

        DrawSphere(Vector3{playerX,y+2.43f,PLAYER_Z-0.03f},0.36f,skin);
        DrawSphere(Vector3{playerX,y+2.58f,PLAYER_Z+0.00f},0.35f,hair);
        DrawSphere(Vector3{playerX-0.21f,y+2.51f,PLAYER_Z-0.03f},0.20f,hair);
        DrawSphere(Vector3{playerX+0.21f,y+2.51f,PLAYER_Z-0.03f},0.20f,hair);
    }
}

static void DrawTree(const Tree &tr, float worldZ) {
    float fog = (-worldZ-18.0f)/145.0f;
    Color fogCol{116,151,139,255};
    Color trunk = Mix(Color{105,72,47,255},fogCol,fog*0.52f);
    Color leaf1 = Mix(tr.variant==0?Color{44,104,65,255}:Color{53,119,73,255},fogCol,fog*0.55f);
    Color leaf2 = Mix(Color{67,137,78,255},fogCol,fog*0.55f);
    float s=tr.scale;
    DrawShadow(Vector3{tr.x,0,worldZ},0.72f*s,0.16f);
    DrawCylinder(Vector3{tr.x,1.25f*s,worldZ},0.23f*s,0.34f*s,2.5f*s,8,trunk);
    DrawCylinder(Vector3{tr.x,2.15f*s,worldZ},0.0f,1.10f*s,2.15f*s,10,leaf1);
    DrawCylinder(Vector3{tr.x+0.12f*s,2.85f*s,worldZ-0.05f},0.0f,0.88f*s,1.75f*s,10,leaf2);
    DrawSphere(Vector3{tr.x-0.45f*s,2.75f*s,worldZ+0.05f},0.48f*s,leaf1);
    DrawSphere(Vector3{tr.x+0.50f*s,2.55f*s,worldZ-0.08f},0.42f*s,leaf2);
}

static void DrawObstacle(const Obstacle &o) {
    Color stone{104,112,109,255};
    Color bark{111,72,44,255};
    Color cut{176,124,74,255};
    Color leaves{58,119,67,255};
    DrawShadow(Vector3{o.x,0,o.z},0.72f,0.18f);
    if (o.type==0) {
        DrawSphere(Vector3{o.x,0.42f,o.z},0.54f,stone);
        DrawSphere(Vector3{o.x-0.28f,0.24f,o.z+0.12f},0.31f,Color{91,101,98,255});
        DrawSphere(Vector3{o.x+0.30f,0.22f,o.z-0.08f},0.27f,Color{122,127,119,255});
    } else if (o.type==1) {
        DrawCylinderEx(Vector3{o.x-0.92f,0.36f,o.z},Vector3{o.x+0.92f,0.36f,o.z},0.34f,0.34f,12,bark);
        DrawSphere(Vector3{o.x-0.92f,0.36f,o.z},0.34f,cut);
        DrawSphere(Vector3{o.x+0.92f,0.36f,o.z},0.34f,cut);
    } else if (o.type==2) {
        DrawCylinder(Vector3{o.x,1.62f,o.z},0.16f,0.18f,3.0f,8,bark);
        DrawSphere(Vector3{o.x-0.64f,1.46f,o.z},0.38f,leaves);
        DrawSphere(Vector3{o.x+0.61f,1.50f,o.z},0.42f,leaves);
        DrawSphere(Vector3{o.x,1.62f,o.z},0.46f,Color{73,139,76,255});
    } else {
        DrawCylinder(Vector3{o.x,0.48f,o.z},0.50f,0.38f,0.96f,12,bark);
        DrawCylinder(Vector3{o.x,0.95f,o.z},0.38f,0.40f,0.05f,12,cut);
        DrawSphere(Vector3{o.x+0.28f,0.43f,o.z+0.10f},0.16f,Color{57,113,61,255});
    }
}

static void DrawCoin3D(const Coin &c) {
    float spin = runTime*145.0f + c.phase*57.0f;
    Color gold{245,188,55,255};
    Color hi{255,223,115,255};
    DrawCylinderEx(Vector3{c.x,c.y,c.z-0.055f},Vector3{c.x,c.y,c.z+0.055f},0.31f,0.31f,18,gold);
    DrawCircle3D(Vector3{c.x,c.y,c.z-0.06f},0.20f,Vector3{0,1,0},spin,hi);
}

static bool HitObstacle(const Obstacle &o) {
    if (!o.active) return false;
    if (fabsf(o.z-PLAYER_Z)>0.72f) return false;
    if (fabsf(o.x-playerX)>0.72f) return false;
    if (o.type==2) return slideTimer<=0.08f;
    return jumpY < ((o.type==1)?0.74f:0.82f);
}

static void UpdateGame(float dt) {
    HandleInput();
    runTime += dt;
    distanceRun += speed*dt;
    speed = 13.5f + fminf(12.5f, distanceRun/165.0f);
    playerX += (LANE_X[targetLane]-playerX) * fminf(1.0f, dt*13.0f);

    if (jumpY>0 || jumpV>0) {
        jumpV -= 20.0f*dt;
        jumpY += jumpV*dt;
        if (jumpY<0) {jumpY=0; jumpV=0;}
    }
    if (slideTimer>0) slideTimer -= dt;

    for (int i=0;i<TREE_COUNT;i++) {
        trees[i].z += speed*dt;
        if (trees[i].z > 10) {
            trees[i].z -= WORLD_SPAN;
            trees[i].x = (i%2?1.0f:-1.0f)*RandF(5.0f,11.5f);
            trees[i].scale = RandF(0.72f,1.42f);
        }
    }
    for (int i=0;i<OBSTACLE_COUNT;i++) {
        obstacles[i].z += speed*dt;
        if (obstacles[i].z > 9.5f) {
            obstacles[i].z -= 190.0f + RandF(0,26);
            obstacles[i].lane=GetRandomValue(0,2);
            obstacles[i].x=LANE_X[obstacles[i].lane];
            obstacles[i].type=GetRandomValue(0,3);
            obstacles[i].active=true;
        }
        if (HitObstacle(obstacles[i])) {
            hitFlash=1.0f;
            int score=(int)distanceRun + coinScore*10;
            if (score>bestScore) bestScore=score;
            state=ScreenState::GameOver;
        }
    }
    for (int i=0;i<COIN_COUNT;i++) {
        coins[i].z += speed*dt;
        if (coins[i].z > 9.5f) {
            coins[i].z -= 185.0f + RandF(0,34);
            coins[i].lane=GetRandomValue(0,2);
            coins[i].x=LANE_X[coins[i].lane];
            coins[i].y=(GetRandomValue(0,5)==0)?1.30f:0.82f;
            coins[i].active=true;
        }
        if (coins[i].active && fabsf(coins[i].z-PLAYER_Z)<0.85f && fabsf(coins[i].x-playerX)<0.72f && fabsf((0.9f+jumpY)-coins[i].y)<1.3f) {
            coins[i].active=false; coinScore++;
        }
    }
}

static void DrawWorld() {
    int sw=GetScreenWidth(), sh=GetScreenHeight();
    DrawRectangleGradientV(0,0,sw,sh,Color{95,151,167,255},Color{196,205,169,255});
    DrawCircle(sw*0.18f,sh*0.13f,42,Color{247,218,144,90});
    DrawCircle(sw*0.18f,sh*0.13f,25,Color{250,224,157,125});

    Camera3D cam{};
    cam.position=Vector3{playerX*0.14f,4.35f,9.9f};
    cam.target=Vector3{playerX*0.08f,1.28f,-7.0f};
    cam.up=Vector3{0,1,0};
    cam.fovy=57.0f;
    cam.projection=CAMERA_PERSPECTIVE;

    BeginMode3D(cam);
    for(int s=0;s<ROAD_SEGMENTS;s++) {
        float z = 7.0f - s*SEGMENT_LEN + fmodf(distanceRun,SEGMENT_LEN);
        if(z>12) z-=WORLD_SPAN;
        DrawPlane(Vector3{0,0,z},Vector2{22.0f,SEGMENT_LEN+0.25f},Color{75,128,71,255});
        DrawPlane(Vector3{0,0.015f,z},Vector2{7.4f,SEGMENT_LEN+0.28f},Color{143,111,73,255});
        DrawPlane(Vector3{0,0.022f,z},Vector2{6.5f,SEGMENT_LEN+0.28f},Color{157,124,81,255});
        DrawCube(Vector3{-3.55f,0.025f,z},0.18f,0.03f,SEGMENT_LEN,Color{91,128,72,110});
        DrawCube(Vector3{ 3.55f,0.025f,z},0.18f,0.03f,SEGMENT_LEN,Color{91,128,72,110});
    }

    for(int pass=0;pass<2;pass++) {
        for(int i=0;i<TREE_COUNT;i++) {
            bool far=trees[i].z<-45;
            if((pass==0)==far) DrawTree(trees[i],trees[i].z);
        }
    }
    for(int i=0;i<OBSTACLE_COUNT;i++) if(obstacles[i].active && obstacles[i].z<8) DrawObstacle(obstacles[i]);
    for(int i=0;i<COIN_COUNT;i++) if(coins[i].active && coins[i].z<8) DrawCoin3D(coins[i]);
    DrawRunner(runTime);
    EndMode3D();
}

static Rectangle CenterButton(float y, float w, float h) {
    return Rectangle{GetScreenWidth()*0.5f-w*0.5f,y,w,h};
}

static bool Pressed(Rectangle r) {
    Vector2 p{}; bool down=false;
    if(GetTouchPointCount()>0){p=GetTouchPosition(0); down=true;}
    else {p=GetMousePosition(); down=IsMouseButtonPressed(MOUSE_BUTTON_LEFT);}
    return down && CheckCollisionPointRec(p,r);
}

static void DrawButton(Rectangle r, const char* text) {
    DrawRectangleRounded(Rectangle{r.x+3,r.y+5,r.width,r.height},0.42f,12,Color{32,45,38,80});
    DrawRectangleRounded(r,0.42f,12,Color{238,181,67,255});
    DrawRectangleRoundedLinesEx(r,0.42f,12,2.0f,Color{255,222,136,255});
    int fs=(int)(r.height*0.34f); int tw=MeasureText(text,fs);
    DrawText(text,(int)(r.x+r.width/2-tw/2),(int)(r.y+r.height/2-fs/2),fs,Color{52,48,36,255});
}

static void DrawHUD() {
    int sw=GetScreenWidth();
    int fs=sw/19;
    DrawRectangleRounded(Rectangle{14,18,(float)sw*0.48f,64},0.32f,10,Color{18,35,29,175});
    char buf[64]; std::snprintf(buf,sizeof(buf),"%05d   C %d",(int)distanceRun,coinScore);
    DrawText(buf,30,37,fs,RAYWHITE);
    Rectangle pause{(float)sw-78,18,60,60};
    DrawRectangleRounded(pause,0.38f,10,Color{18,35,29,175});
    DrawRectangle((int)pause.x+20,(int)pause.y+17,6,26,RAYWHITE);
    DrawRectangle((int)pause.x+34,(int)pause.y+17,6,26,RAYWHITE);
    if(Pressed(pause)) state=ScreenState::Paused;
}

static void DrawMenu() {
    DrawWorld();
    int sw=GetScreenWidth(), sh=GetScreenHeight();
    DrawRectangle(0,0,sw,sh,Color{7,22,18,65});
    int title=sw/8;
    DrawText("FOREST",sw/2-MeasureText("FOREST",title)/2,(int)(sh*0.12f),title,Color{244,238,205,255});
    DrawText("RUSH",sw/2-MeasureText("RUSH",title)/2,(int)(sh*0.12f)+title-5,title,Color{238,177,60,255});
    DrawRectangleRounded(Rectangle{sw*0.17f,sh*0.33f,sw*0.66f,98},0.28f,12,Color{15,38,30,190});
    DrawText("RUN THE WILD",sw/2-MeasureText("RUN THE WILD",sw/22)/2,(int)(sh*0.355f),sw/22,Color{218,229,211,255});
    char b[32]; std::snprintf(b,sizeof(b),"BEST  %d",bestScore);
    DrawText(b,sw/2-MeasureText(b,sw/21)/2,(int)(sh*0.40f),sw/21,RAYWHITE);
    Rectangle play=CenterButton(sh*0.70f,sw*0.66f,82);
    DrawButton(play,"PLAY");
    if(Pressed(play)){ResetWorld(); state=ScreenState::Playing;}
    DrawText("SWIPE TO MOVE / JUMP / SLIDE",sw/2-MeasureText("SWIPE TO MOVE / JUMP / SLIDE",sw/30)/2,(int)(sh*0.82f),sw/30,Color{235,236,215,220});
}

static void DrawPause() {
    DrawWorld(); DrawHUD();
    int sw=GetScreenWidth(),sh=GetScreenHeight();
    DrawRectangle(0,0,sw,sh,Color{5,15,12,145});
    int fs=sw/9; DrawText("PAUSED",sw/2-MeasureText("PAUSED",fs)/2,(int)(sh*0.30f),fs,RAYWHITE);
    Rectangle resume=CenterButton(sh*0.52f,sw*0.62f,78); DrawButton(resume,"RESUME");
    if(Pressed(resume)) state=ScreenState::Playing;
    Rectangle home=CenterButton(sh*0.64f,sw*0.62f,70); DrawButton(home,"HOME");
    if(Pressed(home)) state=ScreenState::Menu;
}

static void DrawGameOver() {
    DrawWorld();
    int sw=GetScreenWidth(),sh=GetScreenHeight();
    DrawRectangle(0,0,sw,sh,Color{8,18,15,135});
    DrawRectangleRounded(Rectangle{sw*0.10f,sh*0.26f,sw*0.80f,sh*0.40f},0.10f,14,Color{18,36,30,225});
    int fs=sw/10; DrawText("RUN OVER",sw/2-MeasureText("RUN OVER",fs)/2,(int)(sh*0.30f),fs,Color{244,229,193,255});
    char s[64]; std::snprintf(s,sizeof(s),"SCORE  %d",(int)distanceRun+coinScore*10);
    DrawText(s,sw/2-MeasureText(s,sw/18)/2,(int)(sh*0.40f),sw/18,RAYWHITE);
    std::snprintf(s,sizeof(s),"BEST   %d",bestScore);
    DrawText(s,sw/2-MeasureText(s,sw/20)/2,(int)(sh*0.45f),sw/20,Color{224,196,111,255});
    Rectangle retry=CenterButton(sh*0.54f,sw*0.62f,76); DrawButton(retry,"RUN AGAIN");
    if(Pressed(retry)){ResetWorld(); state=ScreenState::Playing;}
}

int main() {
    SetConfigFlags(FLAG_MSAA_4X_HINT | FLAG_VSYNC_HINT);
    InitWindow(720,1280,"Forest Rush C++");
    SetTargetFPS(60);
    SetGesturesEnabled(GESTURE_SWIPE_LEFT|GESTURE_SWIPE_RIGHT|GESTURE_SWIPE_UP|GESTURE_SWIPE_DOWN|GESTURE_TAP);
    ResetWorld();

    while(!WindowShouldClose()) {
        float dt=GetFrameTime(); if(dt>0.05f) dt=0.05f;
        if(state==ScreenState::Playing) UpdateGame(dt);
        else runTime += dt*0.55f;
        BeginDrawing();
        ClearBackground(Color{95,151,167,255});
        if(state==ScreenState::Menu) DrawMenu();
        else if(state==ScreenState::Playing){DrawWorld();DrawHUD();}
        else if(state==ScreenState::Paused) DrawPause();
        else DrawGameOver();
        if(hitFlash>0){DrawRectangle(0,0,GetScreenWidth(),GetScreenHeight(),Color{190,64,44,(unsigned char)(hitFlash*80)});hitFlash-=dt*3.0f;}
        EndDrawing();
    }
    CloseWindow();
    return 0;
}
