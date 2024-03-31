from rest_framework.views import APIView
from rest_framework.response import Response
import threading
import math
import random
import numpy as np
from numba import jit
import json
import matplotlib.pyplot as plt
from django.http import JsonResponse

val = 1
a = 1
b = 0
alpha = 1.0

h = 0.01
nstep = 20000
itrans = 10000
pi = 4.0 * math.atan(1.0)

# Initialize omega1 and omega2 with Lorenzian distribution
@jit(nopython=True)
def init_omega(omega, ndim, alpha):
    omega_mean = 0.0
    for i in range(ndim):
        omega[i] = alpha * math.tan((i * pi) / ndim - ((ndim + 1) * pi) / (2 * ndim))
        omega_mean += omega[i]
    return omega_mean / ndim

# Initialize theta1in and theta2in
def init_theta(theta1in, theta2in, ndim):
    for i in range(ndim):
        theta1in[i] = 2 * pi
        theta2in[i] = 2 * pi

@jit(nopython=True)
def derivs(alpha2, lambda2, r1, r2, ndim, omega1, omega2, lambda1, theta1in, theta2in, dydt1, dydt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3):
    sigma1 = 0.0
    sigma2 = 0.0
    sigma3 = 0.0

    for i in range(ndim):
        dydt1[i] = omega1[i] + lambda1 * r1 * math.sin(shi1 - theta1in[i]) + \
                   lambda2 * r1 * r2 * math.sin(shi2 - shi1 - theta1in[i]) + \
                   lambda3 * r1 * r1 * rho1 * math.sin(shi1 - theta1in[i])

        dydt2[i] = omega2[i] + sigma1 * rho1 * math.sin(phi1 - theta2in[i]) + \
                   sigma2 * rho1 * rho2 * math.sin(phi2 - phi1 - theta2in[i]) + \
                   sigma3 * rho1 * rho1 * rho1 * math.sin(phi1 - theta2in[i])

@jit(nopython=True)
def taylor_integration(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, y1, y2, dydt1, dydt2, t, h, yout1, yout2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3):
    hh = h * 0.5
    h6 = h / 6.0
    th = t + hh

    derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, y1, y2, dydt1, dydt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

    yt1 = np.array([y1[i] + hh * dydt1[i] for i in range(n)])
    yt2 = np.array([y2[i] + hh * dydt2[i] for i in range(n)])

    dyt1 = np.zeros(n)
    dyt2 = np.zeros(n)
    derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, yt1, yt2, dyt1, dyt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

    yt1 = np.array([y1[i] + hh * dyt1[i] for i in range(n)])
    yt2 = np.array([y2[i] + hh * dyt2[i] for i in range(n)])

    dym1 = np.zeros(n)
    dym2 = np.zeros(n)
    derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, yt1, yt2, dym1, dym2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

    yt1 = np.array([y1[i] + h * dym1[i] for i in range(n)])
    dym1 = np.array([dyt1[i] + dym1[i] for i in range(n)])
    yt2 = np.array([y2[i] + h * dym2[i] for i in range(n)])
    dym2 = np.array([dyt2[i] + dym2[i] for i in range(n)])

    derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, yt1, yt2, dyt1, dyt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

    for i in range(n):
        yout1[i] = y1[i] + h6 * (dydt1[i] + dyt1[i] + 2.0 * dym1[i])
        yout2[i] = y2[i] + h6 * (dydt2[i] + dyt2[i] + 2.0 * dym2[i])

def calculate_values(ndim, forward=True):
    print('lambda1_min',lambda1_min)
    print('lambda1_max',lambda1_max)
    omega1 = np.zeros(ndim)
    omega2 = np.zeros(ndim)
    theta1in = np.zeros(ndim)
    theta2in = np.zeros(ndim)
    dydt1 = np.zeros(ndim)
    dydt2 = np.zeros(ndim)
    theta1out = np.zeros(ndim)
    theta2out = np.zeros(ndim)
    lambda1_values = []
    r1_array = []
    r2_array = []
    if forward:
        lambda1_values = np.arange(lambda1_min, lambda1_max + 0.1, 0.1)
    else:
        lambda1_values = np.arange(lambda1_max, lambda1_min - 0.05, -0.05)
    print(lambda1_values)
    for lambda1 in lambda1_values:
        r1_final = 0.0
        r2_final = 0.0
        rho1_final = 0.0
        rho2_final = 0.0
        t = 0.0

        # Initialize omega1 and omega2 with Lorenzian distribution
        omega_mean1 = init_omega(omega1, ndim, alpha)
        omega_mean2 = init_omega(omega2, ndim, alpha)

        # Initialize theta1in and theta2in
        init_theta(theta1in, theta2in, ndim)

        # Initialize temporary arrays
        theta1_temp = theta1in.copy()
        theta2_temp = theta2in.copy()

        # Time evolution
        for it in range(1, nstep + 1):
            # Calculate order parameters
            rx1 = np.sum(np.cos(theta1_temp))
            ry1 = np.sum(np.sin(theta1_temp))
            rx2 = np.sum(np.cos(2.0 * theta1_temp))
            ry2 = np.sum(np.sin(2.0 * theta1_temp))
            rhox1 = np.sum(np.cos(theta2_temp))
            rhoy1 = np.sum(np.sin(theta2_temp))
            rhox2 = np.sum(np.cos(2.0 * theta2_temp))
            rhoy2 = np.sum(np.sin(2.0 * theta2_temp))

            r1 = np.sqrt(rx1 ** 2 + ry1 ** 2) / ndim
            r2 = np.sqrt(rx2 ** 2 + ry2 ** 2) / ndim
            rho1 = np.sqrt(rhox1 ** 2 + rhoy1 ** 2) / ndim
            rho2 = np.sqrt(rhox2 ** 2 + rhoy2 ** 2) / ndim
            shi1 = np.arctan2(ry1, rx1)
            shi2 = np.arctan2(ry2, rx2)
            phi1 = np.arctan2(rhoy1, rhox1)
            phi2 = np.arctan2(rhoy2, rhox2)

            # Taylor Integration
            taylor_integration(alpha, lambda2, r1, r2, ndim, omega1, omega2, lambda1, theta1_temp, theta2_temp, dydt1, dydt2, t, h, theta1out, theta2out, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)
            t += h
            theta1_temp = theta1out % (2.0 * pi)
            theta2_temp = theta2out % (2.0 * pi)

            if it > itrans:
                r1_final += r1
                r2_final += r2
                rho1_final += rho1
                rho2_final += rho2

        r1_final /= (nstep - itrans)
        r2_final /= (nstep - itrans)
        rho1_final /= (nstep - itrans)
        rho2_final /= (nstep - itrans)
        r1_array.append(r1_final)
        r2_array.append(r2_final)
        print(f"{lambda1:.6f} {r1_final:.6f} {r2_final:.6f}")

    return lambda1_values, r1_array, r2_array

class __get__k__vs__r__value__(APIView):
    def post(self, request):
        global lambda2, lambda3, lambda1_max, lambda1_min, ndim
        data = request.data
        lambda1_min = data['lambda1_start']
        lambda1_max = data['lambda1_end']
        lambda2 = data['lambda2']
        lambda3 = data['lambda3']
        ndim = data['ndim']

        forward_lambda1, forward_r1, forward_r2 = calculate_values(ndim, forward=True)
        backward_lambda1, backward_r1, backward_r2 = calculate_values(ndim, forward=False)

        # Prepare the response data
        response_data = {
            'forward_lambda1': forward_lambda1.tolist(),
            'forward_r1': forward_r1,
            'forward_r2': forward_r2,
            'backward_lambda1': backward_lambda1.tolist(),
            'backward_r1': backward_r1,
            'backward_r2': backward_r2
        }

        # Return JsonResponse with the response data
        return JsonResponse(response_data)

def __calculate__theta__vs__t__values__(ndim,lambda1,lambda2,lambda3):

    ndim = ndim

    omega1 = np.zeros(ndim)
    omega2 = np.zeros(ndim)
    theta1in = np.zeros(ndim)
    theta2in = np.zeros(ndim)
    dydt1 = np.zeros(ndim)
    dydt2 = np.zeros(ndim)
    theta1out = np.zeros(ndim)
    theta2out = np.zeros(ndim)
    theta1in_unwrapped = np.zeros(ndim)
    theta2in_unwrapped = np.zeros(ndim)
    theta1in_unwrapped = theta1in.copy()
    theta2in_unwrapped = theta2in.copy()

    h = 0.01
    nstep = 2000
    itrans = 1000
    pi = 4.0 * math.atan(1.0)

    # Define your input parameters here...
    val = 1
    a = 1
    b = 0
    lambda2 = lambda2
    lambda3 = lambda3
    lambda1 = lambda1
    alpha = 1.0

    # Initialize omega1 and omega2 with Lorenzian distribution
    @jit(nopython=True)
    def init_omega(omega):
        omega_mean = 0.0
        for i in range(ndim):
            omega[i] = alpha * math.tan((i * pi) / ndim - ((ndim + 1) * pi) / (2 * ndim))
            omega_mean += omega[i]
        return omega_mean / ndim

    omega_mean1 = init_omega(omega1)
    omega_mean2 = init_omega(omega2)

    # Initialize theta1in and theta2in
    for i in range(ndim):
        theta1in[i] = (-pi + 2 * pi * random.random()) + 0.01 * random.uniform(-1, 1)  # Add a small random offset
        theta2in[i] = 2 * pi + 0.01 * random.uniform(-1, 1)


    @jit(nopython=True)
    def derivs(alpha2, lambda2, r1, r2, ndim, omega1, omega2, lambda1, theta1in, theta2in, dydt1, dydt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3):
        sigma1 = 0.0
        sigma2 = 0.0
        sigma3 = 0.0

        for i in range(ndim):
            dydt1[i] = omega1[i] + lambda1 * r1 * math.sin(shi1 - theta1in[i]) + \
                       lambda2 * r1 * r2 * math.sin(shi2 - shi1 - theta1in[i]) + \
                       lambda3 * r1 * r1 * rho1 * math.sin(shi1 - theta1in[i])

            dydt2[i] = omega2[i] + sigma1 * rho1 * math.sin(phi1 - theta2in[i]) + \
                       sigma2 * rho1 * rho2 * math.sin(phi2 - phi1 - theta2in[i]) + \
                       sigma3 * rho1 * rho1 * rho1 * math.sin(phi1 - theta2in[i])

    @jit(nopython=True)
    def taylor_integration(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, y1, y2, dydt1, dydt2, t, h, yout1, yout2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3):
        hh = h * 0.5
        h6 = h / 6.0
        th = t + hh

        derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, y1, y2, dydt1, dydt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

        yt1 = np.array([y1[i] + hh * dydt1[i] for i in range(n)])
        yt2 = np.array([y2[i] + hh * dydt2[i] for i in range(n)])

        dyt1 = np.zeros(n)
        dyt2 = np.zeros(n)
        derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, yt1, yt2, dyt1, dyt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

        yt1 = np.array([y1[i] + hh * dyt1[i] for i in range(n)])
        yt2 = np.array([y2[i] + hh * dyt2[i] for i in range(n)])

        dym1 = np.zeros(n)
        dym2 = np.zeros(n)
        derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, yt1, yt2, dym1, dym2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

        yt1 = np.array([y1[i] + h * dym1[i] for i in range(n)])
        dym1 = np.array([dyt1[i] + dym1[i] for i in range(n)])
        yt2 = np.array([y2[i] + h * dym2[i] for i in range(n)])
        dym2 = np.array([dyt2[i] + dym2[i] for i in range(n)])

        derivs(alpha2, lambda2, r1, r2, n, omega1, omega2, lambda1, yt1, yt2, dyt1, dyt2, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)

        for i in range(n):
            yout1[i] = y1[i] + h6 * (dydt1[i] + dyt1[i] + 2.0 * dym1[i])
            yout2[i] = y2[i] + h6 * (dydt2[i] + dyt2[i] + 2.0 * dym2[i])

    r1_array = []
    r2_array = []

    theta1_time_series = []  # Store theta1in values for plotting
    theta2_time_series = []  # Store theta2in values for plotting

    for lambda1 in [lambda1]:
        r1_final = 0.0
        r2_final = 0.0
        rho1_final = 0.0
        rho2_final = 0.0
        t = 0.0

        theta1_time_series.append([])  # Initialize a list to store theta1in values for this lambda1
        theta2_time_series.append([])  # Initialize a list to store theta2in values for this lambda1

        # Time evolution
        for it in range(1, nstep + 1):
            # Calculate order parameters
            rx1 = np.sum(np.cos(theta1in))
            ry1 = np.sum(np.sin(theta1in))
            rx2 = np.sum(np.cos(2.0 * theta1in))
            ry2 = np.sum(np.sin(2.0 * theta1in))
            rhox1 = np.sum(np.cos(theta2in))
            rhoy1 = np.sum(np.sin(theta2in))
            rhox2 = np.sum(np.cos(2.0 * theta2in))
            rhoy2 = np.sum(np.sin(2.0 * theta2in))

            r1 = np.sqrt(rx1 ** 2 + ry1 ** 2) / ndim
            r2 = np.sqrt(rx2 ** 2 + ry2 ** 2) / ndim
            rho1 = np.sqrt(rhox1 ** 2 + rhoy1 ** 2) / ndim
            rho2 = np.sqrt(rhox2 ** 2 + rhoy2 ** 2) / ndim
            shi1 = np.arctan2(ry1, rx1)
            shi2 = np.arctan2(ry2, rx2)
            phi1 = np.arctan2(rhoy1, rhox1)
            phi2 = np.arctan2(rhoy2, rhox2)

            # Taylor Integration
            taylor_integration(alpha, lambda2, r1, r2, ndim, omega1, omega2, lambda1, theta1in, theta2in, dydt1, dydt2, t, h, theta1out, theta2out, shi1, shi2, rho1, rho2, phi1, phi2, lambda3)
            t += h
            theta1in = theta1out % (2.0 * pi)
            theta2in = theta2out % (2.0 * pi)
            theta1in_unwrapped += dydt1 * h
            theta2in_unwrapped += dydt2 * h

            # Store theta1in_unwrapped and theta2in_unwrapped values for plotting
            theta1_time_series[-1].append(theta1in_unwrapped.copy())
            theta2_time_series[-1].append(theta2in_unwrapped.copy())



            if it > itrans:
                r1_final += r1
                r2_final += r2
                rho1_final += rho1
                rho2_final += rho2

        r1_final /= (nstep - itrans)
        r2_final /= (nstep - itrans)
        rho1_final /= (nstep - itrans)
        rho2_final /= (nstep - itrans)
        r1_array.append(r1_final)
        r2_array.append(r2_final)
        print(f"{lambda1:.6f} {r1_final:.6f} {r2_final:.6f}")

    time_steps = np.arange(nstep) * h
    return theta1_time_series,time_steps

    
import numpy as np

class __get__theta__vs__t__values__(APIView):
    def post(self, request):
        try:
            data = request.data
            lambda1 = float(data.get('lambda1', 0))
            lambda2 = float(data.get('lambda2', 0))
            lambda3 = float(data.get('lambda3', 0))
            ndim = int(data.get('ndim', 0))

            theta1, time = __calculate__theta__vs__t__values__(ndim, lambda1, lambda2, lambda3)

            
            time_list = time.tolist()
            lambda1 = lambda1

            theta_values = []
            for theta in theta1[0]:
                theta_values.append([theta[j] for j in range(ndim)])
            
            response = {
                'theta': theta_values,
                'time': time_list
            }

            return Response(response)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
