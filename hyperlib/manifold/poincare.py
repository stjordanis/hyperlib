import tensorflow as tf
from ..utils.math import tanh, atanh_


class Poincare:

    """
    Implementation of the poincare manifold,. This class can be used for mathematical functions on the poincare manifold.
    """

    def __init__(self,):
        super(Poincare, self).__init__()
        self.name = "PoincareBall"
        self.min_norm = 1e-15
        self.eps = {tf.float32: 4e-3, tf.float64: 1e-5}

    def mobius_matvec(self, m, x, c):
        """
        Generalization for matrix-vector multiplication to hyperbolic space defined as
        math::
            M \otimes_c x = (1/\sqrt{c}) \tanh\left(
                \frac{\|Mx\|_2}{\|x\|_2}\tanh^{-1}(\sqrt{c}\|x\|_2)
            \right)\frac{Mx}{\|Mx\|_2}
        Args:
            m : Tensor for multiplication
            x : Tensor point on poincare ball
            c : Tensor of size 1 representing the hyperbolic curvature.
        Returns
            Mobius matvec result
        """

        sqrt_c = c ** 0.5
        x_norm = tf.norm(x, axis=-1, keepdims=True, ord=2)
        max_num = tf.math.reduce_max(x_norm)
        x_norm = tf.clip_by_value(
            x_norm, clip_value_min=self.min_norm, clip_value_max=max_num
        )
        mx = x @ m
        mx_norm = tf.norm(mx, axis=-1, keepdims=True, ord=2)
        max_num = tf.math.reduce_max(mx_norm)
        mx_norm = tf.clip_by_value(
            mx_norm, clip_value_min=self.min_norm, clip_value_max=max_num
        )

        res_c = (
            tanh(mx_norm / x_norm * atanh_(sqrt_c * x_norm)) * mx / (mx_norm * sqrt_c)
        )
        cond = tf.reduce_prod(
            tf.cast((mx == 0), tf.uint8, name=None), axis=-1, keepdims=True
        )
        res_0 = tf.zeros(1, dtype=res_c.dtype)
        res = tf.where(tf.cast(cond, tf.bool), res_0, res_c)
        return res

    def expmap(self, u, p, c):
        sqrt_c = c ** 0.5
        u_norm = u.norm(dim=-1, p=2, keepdim=True).clamp_min(self.min_norm)
        second_term = (
            tanh(sqrt_c / 2 * self._lambda_x(p, c) * u_norm) * u / (sqrt_c * u_norm)
        )
        gamma_1 = self.mobius_add(p, second_term, c)
        return gamma_1

    def expmap0(self, u, c):
        """
        Hyperbolic exponential map at zero in the Poincare ball model.
          Args:
            u: tensor of size B x dimension representing tangent vectors.
            c: tensor of size 1 representing the hyperbolic curvature.
          Returns:
            Tensor of shape B x dimension.
          """
        sqrt_c = c ** 0.5
        max_num = tf.math.reduce_max(u)
        u_norm = tf.clip_by_value(
            tf.norm(u, axis=-1, ord=2, keepdims=True),
            clip_value_min=self.min_norm,
            clip_value_max=max_num,
        )
        gamma_1 = tf.math.tanh(sqrt_c * u_norm) * u / (sqrt_c * u_norm)
        return gamma_1

    def logmap0(self, p, c):
        """
        Hyperbolic logarithmic map at zero in the Poincare ball model.
        Args:
          p: tensor of size B x dimension representing hyperbolic points.
          c: tensor of size 1 representing the hyperbolic curvature.
        Returns:
          Tensor of shape B x dimension.
        """
        sqrt_c = c ** 0.5
        p_norm = p.norm(axis=-1, ord=2, keepdims=True)
        max_num = tf.math.reduce_max(p_norm)
        p_norm = tf.clip_by_value(
            p_norm, clip_value_min=self.min_norm, clip_value_max=max_num
        )
        scale = 1.0 / sqrt_c * artanh(sqrt_c * p_norm) / p_norm
        return scale * p

    def proj(self, x, c):
        """
        Safe projection on the manifold for numerical stability. This was mentioned in [1]

        Args:
            x : Tensor point on the Poincare ball
            c : Tensor of size 1 representing the hyperbolic curvature.

        Returns:
            Projected vector on the manifold

        References:
            [1] Hyperbolic Neural Networks, NIPS2018
            https://arxiv.org/abs/1805.09112
        """

        x_for_norm = tf.norm(x, axis=-1, keepdims=True, ord=2)
        max_num = tf.math.reduce_max(x_for_norm)
        norm = tf.clip_by_value(
            x_for_norm, clip_value_min=self.min_norm, clip_value_max=max_num
        )
        maxnorm = (1 - self.eps[x.dtype]) / (c ** 0.5)  # tf.math.reduce_max(x)
        cond = norm > maxnorm
        projected = x / norm * maxnorm
        return tf.where(cond, projected, x)

    def mobius_add(self, x, y, c):
        """Element-wise Mobius addition.
      Args:
        x: Tensor of size B x dimension representing hyperbolic points.
        y: Tensor of size B x dimension representing hyperbolic points.
        c: Tensor of size 1 representing the absolute hyperbolic curvature.
      Returns:
        Tensor of shape B x dimension representing the element-wise Mobius addition
        of x and y.
      """
        cx2 = c * tf.reduce_sum(x * x, axis=-1, keepdims=True)
        cy2 = c * tf.reduce_sum(y * y, axis=-1, keepdims=True)
        cxy = c * tf.reduce_sum(x * y, axis=-1, keepdims=True)
        num = (1 + 2 * cxy + cy2) * x + (1 - cx2) * y
        denom = 1 + 2 * cxy + cx2 * cy2
        return self.proj(num / tf.maximum(denom, self.min_norm), c)
